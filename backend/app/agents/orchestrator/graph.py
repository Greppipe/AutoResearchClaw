"""
Master Orchestration Pipeline — LangGraph (FULL UPGRADE)

Execution flow per Master Orchestration Prompt:
  1. journal_intelligence  — pre-flight: extract exact journal submission constraints
  2. extract               — OCR/parse uploaded files
  3. ddi                   — Deep Document Intelligence (embedding + interrogation)
  4. evidence_mapper       — anchor thesis claims to verified DOIs before writing
  5. research              — write full paper (injected with journal constraints + evidence anchors)
  6. data_intelligence     — generate methodology/discussion tables and charts
  7. authenticate          — verify DOIs via CrossRef + Semantic Scholar + Scite
  8. plagiarism            — multi-signal plagiarism + AI detection
  9. humanize              — iterative rewrite until AI < 5%
 10. audit                 — citations, figures, tables, BibTeX
 11. editor                — 7-dimension scoring + targeted repair_jobs dispatch
 12. generate              — Word document + cover letter + reviewer response + report

Repair routing (targeted dispatch):
  Editor returns repair_jobs with precise per-agent instructions.
  repair_jobs are stored in ResearchState and injected into agent context on retry.
  State transitions: QUEUED → RUNNING → VERIFYING → REPAIR_DISPATCHED → APPROVED
  Max iterations: settings.MAX_PIPELINE_ITERATIONS (hard fail-safe).

Token efficiency:
  - JournalIntelligenceAgent uses precise (temp=0) fast model
  - EvidenceMapperAgent uses fast model for claim extraction
  - EditorAgent uses cached writing LLM (prompt caching on large system prompt)
  - RTK hook transparently compresses CLI output tokens
"""
from __future__ import annotations

from datetime import datetime
from typing import TypedDict, List, Optional, Dict, Any, Annotated
import structlog

from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage

from app.agents.journal.agent import JournalIntelligenceAgent
from app.agents.extraction.agent import ExtractionAgent
from app.agents.notebook.agent import DeepDocumentIntelligence
from app.agents.evidence_mapper.agent import EvidenceMapperAgent
from app.agents.research.agent import ResearchAgent
from app.agents.visualization.agent import DataIntelligenceAgent
from app.agents.authentication.agent import AuthenticationAgent
from app.agents.plagiarism.agent import PlagiarismAgent
from app.agents.humanization.agent import HumanizationAgent
from app.agents.audit.agent import AuditAgent
from app.agents.editor.agent import EditorAgent
from app.agents.document.agent import DocumentAgent
from app.core.config import settings

logger = structlog.get_logger()


class ResearchState(TypedDict):
    # ── Project context ────────────────────────────────────────────
    project_id: str
    user_id: str
    title: str
    domain: str
    keywords: List[str]
    objectives: str
    problem_statement: str
    research_gap: str
    hypothesis: str
    novel_contribution: str
    scope: str
    study_type: str
    journal_type: str
    citation_style: str
    preferred_word_count: int
    writing_tone: str
    additional_instructions: str

    # ── Author & ethics metadata ───────────────────────────────────
    author_name: str
    author_affiliation: str
    all_authors: List[Dict[str, str]]
    funding_source: str
    conflicts_of_interest_input: str
    ethics_statement_input: str
    methodology_description: str
    dataset_description: str
    analysis_methods: str
    tools_used: str
    expected_findings: str
    research_significance: str

    # ── Uploaded files ─────────────────────────────────────────────
    uploaded_files_content: List[Dict[str, Any]]
    extracted_data: Dict[str, Any]

    # ── Journal Intelligence (Module 0) ────────────────────────────
    # Populated before any drafting. All agents read this to stay within limits.
    journal_constraints: Dict[str, Any]

    # ── Evidence Anchors (Module 1.5) ──────────────────────────────
    # Pre-mapped DOIs for each thesis claim — injected into ResearchAgent context.
    evidence_anchors: List[Dict[str, Any]]

    # ── Paper content ─────────────────────────────────────────────
    paper_sections: Dict[str, str]
    suggested_figures: List[Dict[str, Any]]
    suggested_tables: List[Dict[str, Any]]
    references: List[Dict[str, Any]]
    figures: List[Dict[str, Any]]
    tables: List[Dict[str, Any]]
    toc: List[Dict[str, Any]]
    bibtex: Optional[str]

    # ── Top-1% paper fields ────────────────────────────────────────
    materials_and_methods: str
    author_contributions: str
    funding_disclosure: str
    conflicts_of_interest: str
    ethics_statement: str
    supplementary_notes: str
    chart_data: List[Dict[str, Any]]
    table_data: List[Dict[str, Any]]

    # ── Data Intelligence visuals ──────────────────────────────────
    methodology_visuals: List[Dict[str, Any]]
    discussion_visuals: List[Dict[str, Any]]

    # ── Deep Document Intelligence ─────────────────────────────────
    ddi_brief: Dict[str, str]
    ddi_chunks: int
    ddi_grounded: bool

    # ── Validation scores ─────────────────────────────────────────
    plagiarism_score: float
    ai_detection_score: float
    trust_score: float
    novelty_score: float

    # ── Editor evaluation ─────────────────────────────────────────
    editor_score: float
    editor_report: Dict[str, Any]
    modules_to_retry: List[str]

    # ── Targeted Repair Dispatch ───────────────────────────────────
    # Structured repair instructions from EditorAgent → injected into agent context on retry.
    # Each job: {agent, dimension, issue, instruction, severity}
    repair_jobs: List[Dict[str, Any]]

    # ── Pipeline control ─────────────────────────────────────────
    iteration: int
    current_step: str
    pipeline_complete: bool
    error: Optional[str]

    # ── Output files ─────────────────────────────────────────────
    output_docx_key: Optional[str]
    output_cover_letter_key: Optional[str]
    output_reviewer_key: Optional[str]
    output_report_key: Optional[str]
    output_bibtex_key: Optional[str]

    # ── Progress ─────────────────────────────────────────────────
    progress_log: List[Dict[str, Any]]
    messages: Annotated[List[BaseMessage], add_messages]


def _log(state: ResearchState, step: str, message: str, pct: float) -> ResearchState:
    state["progress_log"] = state.get("progress_log", []) + [{
        "step": step,
        "message": message,
        "progress_percent": pct,
        "iteration": state.get("iteration", 0),
        "timestamp": datetime.utcnow().isoformat(),
    }]
    state["current_step"] = step
    return state


def _get_repair_instructions(state: ResearchState, agent_name: str) -> str:
    """Extract repair instructions for a specific agent from the repair_jobs list."""
    jobs = state.get("repair_jobs", [])
    agent_jobs = [j for j in jobs if j.get("agent") == agent_name]
    if not agent_jobs:
        return ""
    critical = [j for j in agent_jobs if j.get("severity") == "critical"]
    high = [j for j in agent_jobs if j.get("severity") == "high"]
    # Sort: critical first, then high, then medium
    ordered = critical + high + [j for j in agent_jobs if j.get("severity") not in ("critical", "high")]
    lines = []
    for job in ordered:
        lines.append(
            f"[{job.get('severity', 'medium').upper()}] {job.get('dimension', '').upper()}: "
            f"{job.get('issue', '')} → FIX: {job.get('instruction', '')}"
        )
    return "\n".join(lines)


# ─── Node: Journal Intelligence ───────────────────────────────────────────────

async def journal_intelligence_node(state: ResearchState) -> ResearchState:
    state = _log(state, "journal_intelligence", "Initializing Journal Intelligence — extracting submission constraints...", 2.0)
    result = await JournalIntelligenceAgent().run(state)
    state["journal_constraints"] = result.get("journal_constraints", {})
    jc = state["journal_constraints"]
    state = _log(
        state, "journal_intelligence",
        f"Journal constraints locked: {jc.get('word_limit', '?')} words | "
        f"{jc.get('citation_style', '?').upper()} citations | "
        f"≤{jc.get('figure_limit', '?')} figures | "
        f"≤{jc.get('reference_limit', '?')} refs",
        5.0,
    )
    return state


# ─── Node: Extract ────────────────────────────────────────────────────────────

async def extract_node(state: ResearchState) -> ResearchState:
    state = _log(state, "extracting", "Parsing uploaded files with OCR, Camelot, Unstructured.io...", 8.0)
    result = await ExtractionAgent().run(state)
    state["extracted_data"] = result.get("extracted_data", {})
    state = _log(state, "extracting", "Extraction complete", 12.0)
    return state


# ─── Node: Deep Document Intelligence ────────────────────────────────────────

async def ddi_node(state: ResearchState) -> ResearchState:
    extracted = state.get("extracted_data", {})
    has_docs = bool(extracted) and any(
        extracted.get(k) for k in ("background", "methodology", "data_results", "raw_content", "full_text")
    )
    if not has_docs:
        state = _log(state, "ddi", "No documents uploaded — using user-provided context", 13.0)
        state["ddi_brief"] = {}
        state["ddi_chunks"] = 0
        state["ddi_grounded"] = False
        return state

    state = _log(state, "ddi", "Deep Document Intelligence: embedding + interrogating your documents...", 13.0)
    ddi = DeepDocumentIntelligence()
    result = await ddi.interrogate(state)
    state["ddi_brief"] = result.get("ddi_brief", {})
    state["ddi_chunks"] = result.get("ddi_chunks", 0)
    state["ddi_grounded"] = result.get("ddi_grounded", False)
    state = _log(
        state, "ddi",
        f"DDI complete — {state['ddi_chunks']} chunks indexed, {len(state['ddi_brief'])} questions answered",
        16.0,
    )
    return state


# ─── Node: Evidence Mapper ────────────────────────────────────────────────────

async def evidence_mapper_node(state: ResearchState) -> ResearchState:
    state = _log(state, "evidence_mapping", "Evidence Mapper — anchoring thesis claims to verified DOIs...", 17.0)
    result = await EvidenceMapperAgent().run(state)
    state["evidence_anchors"] = result.get("evidence_anchors", [])
    anchors = state["evidence_anchors"]
    critical = sum(1 for a in anchors if a.get("importance") == "critical")
    state = _log(
        state, "evidence_mapping",
        f"Evidence Mapper complete — {len(anchors)} DOI-verified anchors ({critical} critical claims grounded)",
        20.0,
    )
    return state


# ─── Node: Research ───────────────────────────────────────────────────────────

async def research_node(state: ResearchState) -> ResearchState:
    repair_ctx = _get_repair_instructions(state, "research")
    msg = "Searching 11 literature sources + writing complete Top-1% paper"
    if repair_ctx:
        msg += f" [REPAIR MODE — {len([j for j in state.get('repair_jobs', []) if j.get('agent') == 'research'])} targeted fixes]"
        # Inject repair context into additional_instructions so ResearchAgent sees it
        existing = state.get("additional_instructions", "")
        state["additional_instructions"] = (
            f"{existing}\n\n=== EDITOR REPAIR INSTRUCTIONS (MANDATORY) ===\n{repair_ctx}"
            if existing else f"=== EDITOR REPAIR INSTRUCTIONS (MANDATORY) ===\n{repair_ctx}"
        )

    state = _log(state, "researching", msg + "...", 22.0)
    result = await ResearchAgent().run(state)

    raw_sections = result.get("paper_sections", {})
    VALID_SECTION_KEYS = {
        "abstract", "introduction", "literature_review", "materials_and_methods",
        "methodology", "results", "discussion", "conclusion",
    }
    clean_sections = {
        k: v for k, v in raw_sections.items()
        if k in VALID_SECTION_KEYS and isinstance(v, str)
    }
    if "methodology" in clean_sections and "materials_and_methods" not in clean_sections:
        clean_sections["materials_and_methods"] = clean_sections.pop("methodology")

    state["paper_sections"] = clean_sections

    kw = raw_sections.get("keywords", state.get("keywords", []))
    if isinstance(kw, str):
        kw = [k.strip() for k in kw.split(",") if k.strip()]
    state["keywords"] = kw or state.get("keywords", [])

    state["author_contributions"] = result.get("author_contributions", "")
    state["funding_disclosure"] = result.get("funding_disclosure", state.get("funding_source", ""))
    state["conflicts_of_interest"] = result.get("conflicts_of_interest", state.get("conflicts_of_interest_input", ""))
    state["ethics_statement"] = result.get("ethics_statement", state.get("ethics_statement_input", ""))
    state["supplementary_notes"] = result.get("supplementary_notes", "")
    state["chart_data"] = result.get("chart_data", []) or []
    state["table_data"] = result.get("table_data", []) or []
    state["suggested_figures"] = result.get("suggested_figures", []) or []
    state["suggested_tables"] = result.get("suggested_tables", []) or []
    state["references"] = result.get("references", [])
    state["novelty_score"] = result.get("novelty_score", 0.0)
    state["methodology_visuals"] = result.get("methodology_visuals", []) or []
    state["discussion_visuals"] = result.get("discussion_visuals", []) or []

    state = _log(
        state, "researching",
        f"Paper written — {len(clean_sections)} sections | {len(state['chart_data'])} charts | {len(state['references'])} references",
        42.0,
    )
    return state


# ─── Node: Data Intelligence ──────────────────────────────────────────────────

async def data_intelligence_node(state: ResearchState) -> ResearchState:
    state = _log(state, "data_intelligence", "Generating methodology/discussion tables and charts...", 43.0)
    result = await DataIntelligenceAgent().run(state)
    state["methodology_visuals"] = result.get("methodology_visuals", [])
    state["discussion_visuals"] = result.get("discussion_visuals", [])
    state = _log(
        state, "data_intelligence",
        f"Data Intelligence complete — {len(state['methodology_visuals'])} methodology visuals, "
        f"{len(state['discussion_visuals'])} discussion visuals",
        43.5,
    )
    return state


# ─── Node: Authenticate ───────────────────────────────────────────────────────

async def authenticate_node(state: ResearchState) -> ResearchState:
    repair_ctx = _get_repair_instructions(state, "authenticate")
    if repair_ctx:
        state = _log(state, "authenticating", f"Re-verifying references [REPAIR MODE]...", 44.0)
    else:
        state = _log(state, "authenticating", "Verifying DOIs via CrossRef + Semantic Scholar + Scite...", 44.0)

    result = await AuthenticationAgent().run(state)
    state["references"] = result.get("verified_references", state["references"])
    state["trust_score"] = result.get("trust_score", 0.0)
    state["paper_sections"] = result.get("corrected_sections", state["paper_sections"])
    removed = result.get("retracted_removed", 0) + result.get("predatory_removed", 0)
    state = _log(
        state, "authenticating",
        f"Trust score: {state['trust_score']:.2f} | Removed {removed} bad references",
        56.0,
    )
    return state


# ─── Node: Plagiarism ─────────────────────────────────────────────────────────

async def plagiarism_node(state: ResearchState) -> ResearchState:
    state = _log(state, "plagiarism_check", "Running multi-signal plagiarism + AI detection...", 58.0)
    result = await PlagiarismAgent().run(state)
    state["plagiarism_score"] = result.get("plagiarism_score", 0.0)
    state["ai_detection_score"] = result.get("ai_detection_score", 0.0)
    if result.get("flagged_sections"):
        state["paper_sections"] = {**state["paper_sections"], **result["flagged_sections"]}
    state = _log(
        state, "plagiarism_check",
        f"Plagiarism: {state['plagiarism_score']:.1f}% | AI detected: {state['ai_detection_score']:.1f}%",
        66.0,
    )
    return state


# ─── Node: Humanize ───────────────────────────────────────────────────────────

async def humanize_node(state: ResearchState) -> ResearchState:
    repair_ctx = _get_repair_instructions(state, "humanize")
    msg = "Humanizing content — iterative rewrite until AI < 5%"
    if repair_ctx:
        msg += " [REPAIR MODE — targeted signals]"
    state = _log(state, "humanizing", msg + "...", 68.0)
    result = await HumanizationAgent().run(state)
    state["paper_sections"] = result.get("humanized_sections", state["paper_sections"])
    state["ai_detection_score"] = result.get("new_ai_score", state["ai_detection_score"])
    state = _log(
        state, "humanizing",
        f"Humanization complete — AI score now {state['ai_detection_score']:.1f}%",
        76.0,
    )
    return state


# ─── Node: Audit ──────────────────────────────────────────────────────────────

async def audit_node(state: ResearchState) -> ResearchState:
    repair_ctx = _get_repair_instructions(state, "audit")
    msg = "Auditing figures, tables, TOC, citations, DOIs"
    if repair_ctx:
        msg += " [REPAIR MODE]"
    state = _log(state, "auditing", msg + "...", 78.0)

    audit_state = dict(state)
    audit_state["figures"] = state.get("suggested_figures", [])
    audit_state["tables"] = state.get("suggested_tables", [])
    # Inject journal constraints so audit enforces figure/table limits
    audit_state["journal_constraints"] = state.get("journal_constraints", {})

    result = await AuditAgent().run(audit_state)

    state["paper_sections"] = result.get("audited_sections", state["paper_sections"])
    state["references"] = result.get("audited_references", state["references"])
    state["figures"] = result.get("audited_figures", [])
    state["tables"] = result.get("audited_tables", [])
    state["toc"] = result.get("toc", [])
    state["bibtex"] = result.get("bibtex")

    audit_report = result.get("audit_report", {})
    state = _log(
        state, "auditing",
        f"Audit done — {audit_report.get('total_issues', 0)} issues fixed, "
        f"citation coverage {audit_report.get('citation_audit', {}).get('citation_coverage', 0):.0%}",
        86.0,
    )
    return state


# ─── Node: Editor Review ──────────────────────────────────────────────────────

async def editor_node(state: ResearchState) -> ResearchState:
    iteration = state.get("iteration", 0)
    state = _log(state, "editor_review", f"Editor-in-Chief review — iteration {iteration + 1}...", 88.0)
    result = await EditorAgent().run(state)

    state["editor_score"] = result.get("overall_score", 0.0)
    state["editor_report"] = result
    state["modules_to_retry"] = result.get("modules_to_retry", [])
    # Store structured repair_jobs for targeted dispatch on next iteration
    state["repair_jobs"] = result.get("repair_jobs", [])

    verdict = "PASS" if result.get("pass_threshold") else "RETRY"
    critical_repairs = sum(1 for j in state["repair_jobs"] if j.get("severity") == "critical")
    state = _log(
        state, "editor_review",
        f"Editor score: {state['editor_score']:.1f}/10 — {verdict} | "
        f"{len(state['repair_jobs'])} repair jobs dispatched ({critical_repairs} critical)",
        89.0,
    )
    return state


# ─── Node: Generate Document ──────────────────────────────────────────────────

async def generate_document_node(state: ResearchState) -> ResearchState:
    state = _log(state, "generating", "Generating Word document, cover letter, and editorial report...", 91.0)
    result = await DocumentAgent().run(state)
    state["output_docx_key"] = result.get("docx_key")
    state["output_cover_letter_key"] = result.get("cover_letter_key")
    state["output_reviewer_key"] = result.get("reviewer_response_key")
    state["output_report_key"] = result.get("report_key")
    state["output_bibtex_key"] = result.get("bibtex_key")
    state["pipeline_complete"] = True
    state = _log(state, "completed", f"Paper complete! Editor score: {state['editor_score']:.1f}/10", 100.0)
    return state


# ─── Routing Logic ────────────────────────────────────────────────────────────

def route_after_editor(state: ResearchState) -> str:
    score = state.get("editor_score", 0.0)
    iteration = state.get("iteration", 0)

    if score >= settings.EDITOR_MIN_SCORE:
        return "generate"

    if iteration >= settings.MAX_PIPELINE_ITERATIONS:
        logger.warning("Max iterations reached — forcing generation", score=score, iteration=iteration)
        return "generate"

    # Targeted routing: route to the module with the highest-severity repair job
    repair_jobs = state.get("repair_jobs", [])
    critical_agents = {j["agent"] for j in repair_jobs if j.get("severity") == "critical"}
    high_agents = {j["agent"] for j in repair_jobs if j.get("severity") == "high"}

    modules = state.get("modules_to_retry", [])

    # Check repair_jobs first (more precise than modules_to_retry)
    for priority_set in (critical_agents, high_agents):
        if "research" in priority_set or any(m in modules for m in ("research", "literature", "novelty")):
            return "increment_then_research"
        if "authenticate" in priority_set or any(m in modules for m in ("authenticate", "references", "citations")):
            return "increment_then_authenticate"
        if "plagiarism" in priority_set or any(m in modules for m in ("plagiarism", "ai_detection")):
            return "increment_then_plagiarism"
        if "humanize" in priority_set or any(m in modules for m in ("humanize", "tone", "writing")):
            return "increment_then_humanize"
        if "audit" in priority_set or any(m in modules for m in ("audit", "figures", "tables")):
            return "increment_then_audit"

    # Fall back to modules_to_retry list
    if any(m in modules for m in ("research", "literature", "novelty")):
        return "increment_then_research"
    if any(m in modules for m in ("authenticate", "references", "citations")):
        return "increment_then_authenticate"
    if any(m in modules for m in ("plagiarism", "ai_detection")):
        return "increment_then_plagiarism"
    if any(m in modules for m in ("humanize", "tone", "writing")):
        return "increment_then_humanize"
    if any(m in modules for m in ("audit", "figures", "tables")):
        return "increment_then_audit"

    return "increment_then_research"


# ─── Build Graph ──────────────────────────────────────────────────────────────

def build_pipeline() -> StateGraph:
    g = StateGraph(ResearchState)

    # Register all nodes
    g.add_node("journal_intelligence", journal_intelligence_node)
    g.add_node("extract", extract_node)
    g.add_node("ddi", ddi_node)
    g.add_node("evidence_mapper", evidence_mapper_node)
    g.add_node("research", research_node)
    g.add_node("data_intelligence", data_intelligence_node)
    g.add_node("authenticate", authenticate_node)
    g.add_node("plagiarism", plagiarism_node)
    g.add_node("humanize", humanize_node)
    g.add_node("audit", audit_node)
    g.add_node("editor", editor_node)
    g.add_node("generate", generate_document_node)

    def make_increment_node(target: str):
        async def _node(state: ResearchState) -> ResearchState:
            state["iteration"] = state.get("iteration", 0) + 1
            state = _log(
                state, "retrying",
                f"Targeted repair dispatch → {target} (iteration {state['iteration']}) | "
                f"{sum(1 for j in state.get('repair_jobs', []) if j.get('agent') == target)} repair jobs",
                89.5,
            )
            return state
        return _node

    # Increment-then-route nodes (state mutation in node, not router)
    g.add_node("increment_then_research", make_increment_node("research"))
    g.add_node("increment_then_authenticate", make_increment_node("authenticate"))
    g.add_node("increment_then_plagiarism", make_increment_node("plagiarism"))
    g.add_node("increment_then_humanize", make_increment_node("humanize"))
    g.add_node("increment_then_audit", make_increment_node("audit"))

    # ── Linear forward pipeline ──────────────────────────────────────────────
    g.set_entry_point("journal_intelligence")
    g.add_edge("journal_intelligence", "extract")
    g.add_edge("extract", "ddi")
    g.add_edge("ddi", "evidence_mapper")
    g.add_edge("evidence_mapper", "research")
    g.add_edge("research", "data_intelligence")
    g.add_edge("data_intelligence", "authenticate")
    g.add_edge("authenticate", "plagiarism")
    g.add_edge("plagiarism", "humanize")
    g.add_edge("humanize", "audit")
    g.add_edge("audit", "editor")

    # ── Editor conditional routing (targeted repair dispatch) ────────────────
    g.add_conditional_edges(
        "editor",
        route_after_editor,
        {
            "generate": "generate",
            "increment_then_research": "increment_then_research",
            "increment_then_authenticate": "increment_then_authenticate",
            "increment_then_plagiarism": "increment_then_plagiarism",
            "increment_then_humanize": "increment_then_humanize",
            "increment_then_audit": "increment_then_audit",
        },
    )

    # ── Retry edges (route back to specific module with repair context) ───────
    g.add_edge("increment_then_research", "research")
    g.add_edge("increment_then_authenticate", "authenticate")
    g.add_edge("increment_then_plagiarism", "plagiarism")
    g.add_edge("increment_then_humanize", "humanize")
    g.add_edge("increment_then_audit", "audit")

    g.add_edge("generate", END)
    return g


pipeline_graph = build_pipeline().compile()
