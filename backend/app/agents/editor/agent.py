"""
Editor-in-Chief Agent — Module 8 (ScholarPeer Auditing Upgrade)
Decouples contextualization from critique by deploying:
  - Sub-Domain Historian: Models the scientific narrative trajectory.
  - Baseline Scout: Identifies omitted State-of-the-Art (SOTA) comparisons.
  - Multi-Aspect Q&A Engine: Audits internal logical and statistical consistency.
Main Editor-in-Chief synthesizes these audits into the final publication rubric.
"""
from __future__ import annotations

import json
import asyncio
from typing import Dict, Any, List
import structlog

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import JsonOutputParser

from app.core.config import settings
from app.core.llm_factory import get_cached_writing_llm, make_cached_system, get_fast_llm

logger = structlog.get_logger()

# ─── ScholarPeer Auditing Prompts ──────────────────────────────────────────────

HISTORIAN_PROMPT = """You are a Sub-Domain Historian for a top-tier scientific journal.
Your job is to model the narrative trajectory of the scientific sub-field and evaluate the manuscript's context.

Review the manuscript's Title, Abstract, Introduction, and Literature Review.
Identify:
1. Contextual Gaps: Are there major historical theories or background discoveries omitted?
2. Narrative Trajectory: Does the paper align with the current logical evolution of this field?
3. Outdated Assumptions: Does the paper rely on debunked or obsolete methodologies?

Return ONLY a JSON audit report:
{
  "contextual_gaps": ["<gap 1>", ...],
  "narrative_fit_assessment": "<brief analysis of the paper's fit in the field's trajectory>",
  "historical_recommendations": ["<recommendation 1>", ...]
}"""

SCOUT_PROMPT = """You are a Baseline Scout for a top-tier scientific journal.
Your job is to identify whether the manuscript compares itself to the proper state-of-the-art (SOTA) baselines.

Review the Methodology, Results, and Discussion sections, as well as the References.
Identify:
1. Omitted SOTA: Are there standard, high-impact baseline methods from recent years (2020-2025) that are missing from the comparison?
2. Benchmarking Rigor: Is the comparison fair and statistically robust?

Return ONLY a JSON audit report:
{
  "omitted_baselines": ["<baseline method / paper title>", ...],
  "benchmarking_rigor_assessment": "<brief analysis of the comparative rigor>",
  "benchmarking_recommendations": ["<recommendation 1>", ...]
}"""

QA_PROMPT = """You are a Multi-Aspect Q&A Engine for a top-tier scientific journal.
Your job is to act as an adversarial debugger to find internal logical or statistical contradictions.

Review all sections of the manuscript.
Check:
1. Statistical Consistency: Do the reported sample sizes, feature dimensions, p-values, and effect sizes in the text match the tables and figures?
2. Claim Consistency: Does the Abstract or Discussion make claims that are not supported by the Methodology or Results?
3. Mathematical Logic: Are there mathematical or logic gaps in the methodology or equations?

Return ONLY a JSON audit report:
{
  "inconsistencies": ["<inconsistency 1>", ...],
  "statistical_validity_assessment": "<brief analysis of statistical soundness>",
  "logic_recommendations": ["<recommendation 1>", ...]
}"""


# ─── Main Editor-in-Chief System Prompt ────────────────────────────────────────

EDITOR_SYSTEM = """You are the Editor-in-Chief of a top-5 SCI journal (e.g., Nature, IEEE Transactions, Elsevier Neurocomputing).

Your job is to evaluate if this paper is ready for publication.
To do this, you will receive the manuscript draft and the reports of three specialized sub-auditors:
1. The Sub-Domain Historian (assessing context and narrative trajectory)
2. The Baseline Scout (assessing SOTA comparisons and benchmarks)
3. The Multi-Aspect Q&A Engine (assessing internal logical and statistical consistency)

Synthesize these reports along with the manuscript text to compile the final decision.

Scoring rubric (be STRICT — 9.0+ means genuinely publishable TODAY):
- 9.5–10.0: Accept as-is. Exceptional novelty, rigorous methodology, publication-ready writing.
- 9.0–9.4:  Accept with trivial formatting fixes only.
- 7.0–8.9:  Major/minor revisions. Clear weaknesses in one or more areas.
- 5.0–6.9:  Reject and resubmit. Fundamental gaps.
- 0–4.9:    Reject. Methodological flaws, lack of novelty, or poor quality.

Evaluate ALL seven dimensions independently:
1. NOVELTY (0–10): Is the contribution genuinely new? Does it advance the field?
2. METHODOLOGY (0–10): Is the research design sound, reproducible, and rigorous?
3. CLARITY (0–10): Is the writing clear, precise, and academically excellent?
4. LITERATURE (0–10): Is the literature review comprehensive and critically analysed?
5. RESULTS (0–10): Are findings presented clearly with appropriate statistics/evidence?
6. TECHNICAL_DEPTH (0–10): Is the technical content sophisticated enough for a top journal?
7. JOURNAL_READINESS (0–10): Does it meet the target journal's formatting, structure, and citation standards?

overall_score = weighted average:
  novelty×0.25 + methodology×0.20 + clarity×0.15 + literature×0.15 + results×0.10 + technical_depth×0.10 + journal_readiness×0.05

TARGETED REPAIR DISPATCH RULES:
For every weakness identified by yourself or the sub-auditors, you MUST generate a repair_job with:
- agent: exact module name (research|authenticate|plagiarism|humanize|audit)
- dimension: which scoring dimension this fixes
- issue: what exactly is wrong (be specific — cite section names, line patterns, exact deficiency)
- instruction: mathematically precise fix instruction (cite word counts, citation counts, p-value requirements, exact text patterns to change)
- severity: critical|high|medium

Return ONLY valid JSON:
{
  "overall_score": <float>,
  "novelty_score": <float>,
  "methodology_score": <float>,
  "clarity_score": <float>,
  "literature_score": <float>,
  "results_score": <float>,
  "technical_depth_score": <float>,
  "journal_readiness_score": <float>,
  "acceptance_probability": <float 0–1>,
  "strengths": ["<s1>", "<s2>", "<s3>"],
  "weaknesses": ["<w1>", "<w2>", "<w3>"],
  "recommendations": ["<r1>", "<r2>", "<r3>"],
  "section_feedback": {
    "abstract": "<specific, actionable feedback>",
    "introduction": "<specific, actionable feedback>",
    "literature_review": "<specific, actionable feedback>",
    "methodology": "<specific, actionable feedback>",
    "results": "<specific, actionable feedback>",
    "discussion": "<specific, actionable feedback>",
    "conclusion": "<specific, actionable feedback>",
    "references": "<specific, actionable feedback>"
  },
  "repair_jobs": [
    {
      "agent": "<research|authenticate|plagiarism|humanize|audit>",
      "dimension": "<novelty|methodology|clarity|literature|results|technical_depth|journal_readiness>",
      "issue": "<specific description of the exact problem>",
      "instruction": "<precise, actionable fix — include word counts, citation numbers, statistical thresholds>",
      "severity": "<critical|high|medium>"
    }
  ],
  "modules_to_retry": ["<module_name>", ...],
  "pass_threshold": <boolean>
}

module names (use exact strings): research, authenticate, plagiarism, humanize, audit
Do NOT output markdown formatting blocks, return ONLY the raw JSON."""


class EditorAgent:
    def __init__(self):
        self.llm = get_cached_writing_llm(max_tokens=4096)
        self.fast_llm = get_fast_llm(max_tokens=2048)

    def _format_journal_constraints(self, state: Dict[str, Any]) -> str:
        jc = state.get("journal_constraints", {})
        if not jc:
            return "Journal constraints: Not specified (applying general SCI standards)"
        return (
            f"TARGET JOURNAL CONSTRAINTS\n"
            f"===========================\n"
            f"Word Limit: {jc.get('word_limit', 'N/A')} words (body, excl. references)\n"
            f"Abstract Limit: {jc.get('abstract_limit', 'N/A')} words\n"
            f"Figure Limit: {jc.get('figure_limit', 'N/A')}\n"
            f"Table Limit: {jc.get('table_limit', 'N/A')}\n"
            f"Reference Limit: {jc.get('reference_limit', 'N/A')}\n"
            f"Citation Style: {jc.get('citation_style', 'N/A').upper()} — {jc.get('citation_format_description', '')}\n"
            f"Required Sections: {', '.join(jc.get('required_sections', []))}\n"
            f"Keywords Required: {'Yes (' + str(jc.get('keywords_limit', 0)) + ' max)' if jc.get('keywords_limit', 0) > 0 else 'No'}\n"
            f"Impact Factor Range: {jc.get('impact_factor_range', 'N/A')}\n"
            f"Acceptance Rate: {jc.get('acceptance_rate', 0) * 100:.0f}%\n"
            f"Notes: {jc.get('notes', 'None')}"
        )

    def _format_evidence_anchor_summary(self, state: Dict[str, Any]) -> str:
        anchors = state.get("evidence_anchors", [])
        if not anchors:
            return "Evidence anchors: None pre-mapped (Evidence Mapper not run)"
        critical = [a for a in anchors if a.get("importance") == "critical"]
        high = [a for a in anchors if a.get("importance") == "high"]
        return (
            f"Evidence Anchors (pre-mapped DOIs): {len(anchors)} total "
            f"({len(critical)} critical, {len(high)} high importance)\n"
            f"Sample critical anchors: " +
            ", ".join(f'"{a["title"][:50]}" ({a["doi"]})' for a in critical[:3])
        )

    def _build_content(self, state: Dict[str, Any]) -> str:
        sections = state.get("paper_sections", {})
        references = state.get("references", [])
        figures = state.get("figures", [])
        tables = state.get("tables", [])

        ref_count = len(references)
        verified_refs = sum(1 for r in references if r.get("verified"))
        avg_trust = sum(r.get("trust_score", 0) for r in references) / max(ref_count, 1)

        def _section(key: str, label: str) -> str:
            text = sections.get(key, "")
            if not text:
                return f"\n== {label} ==\n[MISSING — CRITICAL DEDUCTION]\n"
            wc = len(text.split())
            return f"\n== {label} ({wc} words) ==\n{text}\n"

        return f"""
PAPER EVALUATION BRIEF
======================
Title: {state.get('title', '')}
Domain: {state.get('domain', '')}
Journal Target: {state.get('journal_type', '').upper()}
Pipeline Iteration: {state.get('iteration', 0)}

{self._format_journal_constraints(state)}

VALIDATION METRICS
==================
Plagiarism Score: {state.get('plagiarism_score', 0):.1f}% (pass = <15%)
AI Detection Score: {state.get('ai_detection_score', 0):.1f}% (pass = <5%)
Reference Trust Score: {avg_trust:.2f}/1.0
Verified References: {verified_refs}/{ref_count}
Novelty Score (pre-eval): {state.get('novelty_score', 0):.1f}/10
Figures: {len(figures)} | Tables: {len(tables)}

{self._format_evidence_anchor_summary(state)}

REPAIR CONTEXT (from prior iteration)
======================================
Prior repair_jobs: {json.dumps(state.get('repair_jobs', []), indent=2) if state.get('repair_jobs') else 'None (first pass)'}

PAPER CONTENT
=============
{_section('abstract', 'ABSTRACT')}
{_section('introduction', 'INTRODUCTION')}
{_section('literature_review', 'LITERATURE REVIEW')}
{_section('materials_and_methods', 'MATERIALS & METHODS')}
{_section('results', 'RESULTS')}
{_section('discussion', 'DISCUSSION')}
{_section('conclusion', 'CONCLUSION')}

REFERENCES SAMPLE (first 20)
=============================
{json.dumps([
    {
        'n': i + 1,
        'title': r.get('title', ''),
        'year': r.get('year'),
        'journal': r.get('journal', ''),
        'verified': r.get('verified', False),
        'trust': round(r.get('trust_score', 0), 2),
    }
    for i, r in enumerate(references[:20])
], indent=2)}
"""

    async def _run_sub_auditor(self, prompt: str, content: str) -> Dict[str, Any]:
        messages = [
            SystemMessage(content=prompt),
            HumanMessage(content=f"Analyze the following manuscript details:\n\n{content}")
        ]
        chain = self.fast_llm | JsonOutputParser()
        try:
            return await chain.ainvoke(messages)
        except Exception as e:
            logger.warning("Sub-auditor failed", error=str(e))
            return {}

    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        content = self._build_content(state)

        # ─── ScholarPeer Auditing Phase (Parallel Execution) ──────────────────
        logger.info("EditorAgent: Dispatching ScholarPeer sub-auditors in parallel...")
        historian_task = self._run_sub_auditor(HISTORIAN_PROMPT, content)
        scout_task = self._run_sub_auditor(SCOUT_PROMPT, content)
        qa_task = self._run_sub_auditor(QA_PROMPT, content)

        historian_report, scout_report, qa_report = await asyncio.gather(
            historian_task, scout_task, qa_task
        )
        logger.info("EditorAgent: ScholarPeer auditing complete.")

        # Format audits for the main Editor-in-Chief
        peer_audits = f"""
=== SCHOLARPEER SUB-AUDIT REPORTS ===
1. SUB-DOMAIN HISTORIAN REPORT:
{json.dumps(historian_report, indent=2)}

2. BASELINE SCOUT REPORT:
{json.dumps(scout_report, indent=2)}

3. MULTI-ASPECT Q&A ENGINE REPORT:
{json.dumps(qa_report, indent=2)}
====================================
"""

        messages = [
            SystemMessage(content=make_cached_system(EDITOR_SYSTEM)),
            HumanMessage(content=f"Evaluate this scientific paper submission:\n\n{content}\n\n{peer_audits}"),
        ]
        chain = self.llm | JsonOutputParser()

        try:
            report = await chain.ainvoke(messages)
        except Exception as e:
            logger.error("Editor evaluation failed", error=str(e))
            report = {
                "overall_score": 4.5,
                "novelty_score": 5.0, "methodology_score": 5.0, "clarity_score": 5.0,
                "literature_score": 5.0, "results_score": 4.0, "technical_depth_score": 4.5,
                "journal_readiness_score": 4.0,
                "acceptance_probability": 0.1,
                "strengths": ["Paper was generated"],
                "weaknesses": ["Evaluation failed — full retry required"],
                "recommendations": ["Retry research and humanization modules"],
                "section_feedback": {},
                "repair_jobs": [
                    {
                        "agent": "research",
                        "dimension": "novelty",
                        "issue": "Editor evaluation call failed — cannot assess paper quality",
                        "instruction": "Regenerate all sections with increased analytical depth and more primary citations",
                        "severity": "critical",
                    }
                ],
                "modules_to_retry": ["research", "humanize"],
                "pass_threshold": False,
            }

        # ── Hard penalties for failing validation gates ──────────────────────
        plagiarism = state.get("plagiarism_score", 0.0)
        ai_score = state.get("ai_detection_score", 0.0)
        trust = state.get("trust_score", 0.0)
        ref_count = len(state.get("references", []))
        verified = sum(1 for r in state.get("references", []) if r.get("verified"))

        repair_jobs: List[Dict] = list(report.get("repair_jobs", []))

        if plagiarism > 30.0:
            report["overall_score"] = min(report.get("overall_score", 5.0), 4.5)
            report.setdefault("weaknesses", []).append(f"FAIL: Plagiarism {plagiarism:.1f}% >> 15% threshold")
            report["modules_to_retry"] = list(set(report.get("modules_to_retry", []) + ["plagiarism", "humanize"]))
            repair_jobs.append({
                "agent": "humanize",
                "dimension": "clarity",
                "issue": f"Plagiarism score {plagiarism:.1f}% exceeds 15% threshold",
                "instruction": f"Rewrite all flagged sections with >30% overlap. Paraphrase using synonymous technical vocabulary. Target plagiarism <10%.",
                "severity": "critical",
            })
        elif plagiarism > 15.0:
            report["overall_score"] = min(report.get("overall_score", 7.0), 6.5)
            report["modules_to_retry"] = list(set(report.get("modules_to_retry", []) + ["humanize"]))
            repair_jobs.append({
                "agent": "humanize",
                "dimension": "clarity",
                "issue": f"Plagiarism score {plagiarism:.1f}% exceeds 15% threshold",
                "instruction": "Rephrase sections with >15% similarity. Vary sentence structure and vocabulary. Target <10%.",
                "severity": "high",
            })

        if ai_score > 20.0:
            report["overall_score"] = min(report.get("overall_score", 5.0), 5.0)
            report.setdefault("weaknesses", []).append(f"FAIL: AI detection {ai_score:.1f}% >> 5% threshold")
            report["modules_to_retry"] = list(set(report.get("modules_to_retry", []) + ["humanize"]))
            repair_jobs.append({
                "agent": "humanize",
                "dimension": "clarity",
                "issue": f"AI detection score {ai_score:.1f}% far exceeds 5% threshold",
                "instruction": "Apply full 7-signal humanization pass: increase entropy variance, burstiness, TTR diversity, reduce passive voice below 20%, add first-person researcher perspective in Discussion.",
                "severity": "critical",
            })
        elif ai_score > 5.0:
            report["overall_score"] = min(report.get("overall_score", 7.5), 7.5)
            report["modules_to_retry"] = list(set(report.get("modules_to_retry", []) + ["humanize"]))
            repair_jobs.append({
                "agent": "humanize",
                "dimension": "clarity",
                "issue": f"AI detection score {ai_score:.1f}% exceeds 5% threshold",
                "instruction": "Increase burstiness and n-gram diversity. Target AI score <5% on all 7 heuristic signals.",
                "severity": "high",
            })

        if trust < 0.4 and ref_count > 5:
            report["overall_score"] = min(report.get("overall_score", 6.0), 6.0)
            report.setdefault("weaknesses", []).append(f"Low reference trust score: {trust:.2f}")
            report["modules_to_retry"] = list(set(report.get("modules_to_retry", []) + ["authenticate"]))
            repair_jobs.append({
                "agent": "authenticate",
                "dimension": "literature",
                "issue": f"Average reference trust score {trust:.2f} below 0.4 threshold. {ref_count - verified}/{ref_count} references unverified.",
                "instruction": f"Re-verify all {ref_count - verified} unverified references against CrossRef DOI API. Remove any predatory journal citations. Replace with verified alternatives from IEEE/Elsevier/Springer publishers.",
                "severity": "high",
            })

        if ref_count < 15:
            report["overall_score"] = min(report.get("overall_score", 6.5), 6.5)
            report.setdefault("weaknesses", []).append(f"Insufficient references: {ref_count} (need ≥15)")
            report["modules_to_retry"] = list(set(report.get("modules_to_retry", []) + ["research"]))
            repair_jobs.append({
                "agent": "research",
                "dimension": "literature",
                "issue": f"Only {ref_count} references found. SCI journals require minimum 20-40 references.",
                "instruction": f"Add {max(0, 25 - ref_count)} more primary research papers from Semantic Scholar and CrossRef. Focus on papers from 2020-2025 with DOIs. Integrate citations naturally into the Literature Review and Discussion.",
                "severity": "critical" if ref_count < 10 else "high",
            })

        # Check journal constraint compliance
        jc = state.get("journal_constraints", {})
        if jc:
            fig_limit = jc.get("figure_limit", 999)
            figures = state.get("figures", [])
            if len(figures) > fig_limit:
                repair_jobs.append({
                    "agent": "audit",
                    "dimension": "journal_readiness",
                    "issue": f"Paper has {len(figures)} figures but journal allows maximum {fig_limit}",
                    "instruction": f"Consolidate or remove {len(figures) - fig_limit} figures. Merge related panels into composite figures. Move non-essential figures to supplementary material.",
                    "severity": "high",
                })

        report["repair_jobs"] = repair_jobs

        # ── Final score and pass threshold ───────────────────────────────────
        final_score = float(report.get("overall_score", 0.0))
        report["overall_score"] = round(final_score, 2)
        report["pass_threshold"] = final_score >= settings.EDITOR_MIN_SCORE

        if final_score >= 9.5:
            report["acceptance_probability"] = 0.95
        elif final_score >= 9.0:
            report["acceptance_probability"] = 0.85
        elif final_score >= 7.5:
            report["acceptance_probability"] = 0.55
        elif final_score >= 6.0:
            report["acceptance_probability"] = 0.25
        else:
            report["acceptance_probability"] = 0.05

        logger.info(
            "Editor review complete",
            score=final_score,
            pass_threshold=report["pass_threshold"],
            iteration=state.get("iteration"),
            repair_jobs=len(repair_jobs),
            modules_to_retry=report.get("modules_to_retry", []),
        )
        return report

