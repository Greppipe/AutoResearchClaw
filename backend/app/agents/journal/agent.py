"""
Journal Intelligence Agent — Module 0 (Pre-Flight)
Extracts exact submission constraints for the target journal BEFORE any drafting.
Enforces word limits, citation style, figure/table caps, section requirements.
Uses a curated constraint database + LLM fallback for unknown journals.
"""
from __future__ import annotations

import json
from typing import Dict, Any
import structlog

from app.core.llm_factory import get_precise_llm

logger = structlog.get_logger()

# ── Curated SCI Journal Constraint Database ──────────────────────────────────
# Covers the most common target journal families. Values represent HARD limits.

JOURNAL_DB: Dict[str, Dict[str, Any]] = {
    "nature": {
        "word_limit": 3000, "abstract_limit": 150, "figure_limit": 6,
        "table_limit": 2, "reference_limit": 50, "citation_style": "nature",
        "required_sections": ["abstract", "introduction", "results", "discussion", "methods"],
        "keywords_limit": 0, "h_index_min": 50, "impact_factor_range": [40, 70],
        "acceptance_rate": 0.07,
        "notes": "Results and Discussion are separate. Methods goes at end. No subheadings in Abstract.",
    },
    "science": {
        "word_limit": 2500, "abstract_limit": 125, "figure_limit": 5,
        "table_limit": 2, "reference_limit": 45, "citation_style": "science",
        "required_sections": ["abstract", "introduction", "results", "discussion", "materials_and_methods"],
        "keywords_limit": 0, "h_index_min": 45, "impact_factor_range": [35, 65],
        "acceptance_rate": 0.06,
        "notes": "Extremely concise. Supplementary material expected for full methods.",
    },
    "ieee": {
        "word_limit": 8000, "abstract_limit": 200, "figure_limit": 15,
        "table_limit": 10, "reference_limit": 60, "citation_style": "ieee",
        "required_sections": ["abstract", "introduction", "related_work", "methodology", "results", "conclusion"],
        "keywords_limit": 6, "h_index_min": 10, "impact_factor_range": [2, 12],
        "acceptance_rate": 0.30,
        "notes": "Index Terms required. References numbered [1] style. Double-column layout.",
    },
    "elsevier": {
        "word_limit": 9000, "abstract_limit": 300, "figure_limit": 12,
        "table_limit": 8, "reference_limit": 80, "citation_style": "apa",
        "required_sections": ["abstract", "introduction", "literature_review", "materials_and_methods", "results", "discussion", "conclusion"],
        "keywords_limit": 6, "h_index_min": 8, "impact_factor_range": [1.5, 10],
        "acceptance_rate": 0.25,
        "notes": "Highlights (3-5 bullet points) required. Author contributions, CoI, funding mandatory.",
    },
    "springer": {
        "word_limit": 8000, "abstract_limit": 250, "figure_limit": 10,
        "table_limit": 6, "reference_limit": 70, "citation_style": "apa",
        "required_sections": ["abstract", "introduction", "methods", "results", "discussion", "conclusion"],
        "keywords_limit": 5, "h_index_min": 8, "impact_factor_range": [1, 8],
        "acceptance_rate": 0.28,
        "notes": "Structured abstract may be required for medical journals. Check journal-specific guidelines.",
    },
    "plos": {
        "word_limit": 10000, "abstract_limit": 300, "figure_limit": 15,
        "table_limit": 10, "reference_limit": 100, "citation_style": "vancouver",
        "required_sections": ["abstract", "introduction", "materials_and_methods", "results", "discussion"],
        "keywords_limit": 10, "h_index_min": 5, "impact_factor_range": [2, 6],
        "acceptance_rate": 0.45,
        "notes": "Structured Abstract with Background/Methodology/Results/Conclusions headers. Open access.",
    },
    "mdpi": {
        "word_limit": 12000, "abstract_limit": 200, "figure_limit": 20,
        "table_limit": 15, "reference_limit": 100, "citation_style": "mdpi",
        "required_sections": ["abstract", "introduction", "materials_and_methods", "results", "discussion", "conclusion"],
        "keywords_limit": 8, "h_index_min": 3, "impact_factor_range": [1, 5],
        "acceptance_rate": 0.55,
        "notes": "Article Processing Charge applies. Author contributions in CRediT format required.",
    },
    "wiley": {
        "word_limit": 7500, "abstract_limit": 250, "figure_limit": 12,
        "table_limit": 8, "reference_limit": 75, "citation_style": "apa",
        "required_sections": ["abstract", "introduction", "methods", "results", "discussion", "conclusion"],
        "keywords_limit": 6, "h_index_min": 7, "impact_factor_range": [2, 9],
        "acceptance_rate": 0.30,
        "notes": "Colour figures may incur charge in print. Check for structured abstract requirement.",
    },
    "taylor_francis": {
        "word_limit": 8000, "abstract_limit": 200, "figure_limit": 10,
        "table_limit": 8, "reference_limit": 60, "citation_style": "apa",
        "required_sections": ["abstract", "introduction", "methods", "results", "discussion", "conclusion"],
        "keywords_limit": 6, "h_index_min": 5, "impact_factor_range": [1, 6],
        "acceptance_rate": 0.35,
        "notes": "Disclosure statement required. Spelling: follow journal's regional style (UK/US).",
    },
    "scopus": {
        "word_limit": 8000, "abstract_limit": 250, "figure_limit": 12,
        "table_limit": 8, "reference_limit": 70, "citation_style": "apa",
        "required_sections": ["abstract", "introduction", "literature_review", "methodology", "results", "discussion", "conclusion"],
        "keywords_limit": 6, "h_index_min": 5, "impact_factor_range": [0.5, 5],
        "acceptance_rate": 0.40,
        "notes": "Scopus-indexed journals vary. These are conservative defaults — verify per-journal.",
    },
    "pubmed": {
        "word_limit": 7000, "abstract_limit": 300, "figure_limit": 8,
        "table_limit": 6, "reference_limit": 60, "citation_style": "vancouver",
        "required_sections": ["abstract", "introduction", "materials_and_methods", "results", "discussion"],
        "keywords_limit": 8, "h_index_min": 5, "impact_factor_range": [1, 15],
        "acceptance_rate": 0.35,
        "notes": "ICMJE authorship criteria apply. CONSORT/PRISMA/STROBE checklists may be required.",
    },
    "lancet": {
        "word_limit": 4000, "abstract_limit": 200, "figure_limit": 5,
        "table_limit": 3, "reference_limit": 50, "citation_style": "vancouver",
        "required_sections": ["abstract", "introduction", "methods", "results", "discussion"],
        "keywords_limit": 0, "h_index_min": 30, "impact_factor_range": [20, 60],
        "acceptance_rate": 0.05,
        "notes": "Research in context panel required. Panel: Evidence before study + Added value.",
    },
    "bmj": {
        "word_limit": 3500, "abstract_limit": 300, "figure_limit": 4,
        "table_limit": 4, "reference_limit": 40, "citation_style": "vancouver",
        "required_sections": ["abstract", "introduction", "methods", "results", "discussion"],
        "keywords_limit": 0, "h_index_min": 25, "impact_factor_range": [15, 40],
        "acceptance_rate": 0.07,
        "notes": "Structured abstract: Objective/Design/Setting/Participants/Interventions/Results/Conclusions.",
    },
}

# Citation style → BibTeX/Word format mapping
CITATION_FORMAT_MAP = {
    "apa": "APA 7th Edition (Author, Year) in-text; full reference list",
    "ieee": "IEEE [1] numeric superscript; numbered reference list",
    "vancouver": "Vancouver [1] numeric; ICMJE format reference list",
    "nature": "Nature superscript numbers; shortened reference format",
    "science": "Science superscript numbers; author-et-al format",
    "mdpi": "MDPI (Author, Year); APA-like with MDPI specifics",
    "chicago": "Chicago Author-Date; bibliography format",
    "harvard": "Harvard (Author Year); reference list",
}


class JournalIntelligenceAgent:
    """
    Pre-flight agent: determines hard submission constraints for the target journal
    before any chapter session begins. This prevents post-hoc reformatting and
    ensures all sub-agents operate within the correct envelope from the start.
    """

    def __init__(self):
        self.llm = get_precise_llm(max_tokens=2048)

    def _lookup_db(self, journal_type: str) -> Dict[str, Any] | None:
        jt = journal_type.lower().strip()

        # Generic category aliases — "SCI", "WOS", "Q1", etc. → Elsevier defaults
        GENERIC_ALIASES = {"sci", "sci journal", "wos", "web of science", "q1", "q2",
                           "scopus indexed", "esci", "general", "international journal"}
        if jt in GENERIC_ALIASES or jt.startswith("sci ") or jt.endswith(" sci"):
            return JOURNAL_DB["elsevier"]

        # Direct match
        if jt in JOURNAL_DB:
            return JOURNAL_DB[jt]

        # Partial match — require the key to be at least 4 chars to avoid false hits
        for key, constraints in JOURNAL_DB.items():
            if len(key) >= 4 and (key in jt or jt in key):
                return constraints
        return None

    async def _infer_constraints(self, journal_type: str, domain: str) -> Dict[str, Any]:
        prompt = f"""You are a scientific publishing expert. Given this target journal/venue:
Journal: {journal_type}
Domain: {domain}

Return a JSON object with EXACT submission constraints. Be precise — use the journal's actual published guidelines.

Return ONLY valid JSON with these fields:
{{
  "word_limit": <int — total body word count, excluding references>,
  "abstract_limit": <int — abstract word limit>,
  "figure_limit": <int — max figures including panels>,
  "table_limit": <int — max tables>,
  "reference_limit": <int — max references, or 999 if unlimited>,
  "citation_style": "<apa|ieee|vancouver|nature|science|chicago|harvard|mdpi>",
  "required_sections": ["<section_key>", ...],
  "keywords_limit": <int — 0 if not required>,
  "impact_factor_range": [<min_float>, <max_float>],
  "acceptance_rate": <float 0-1>,
  "notes": "<any critical formatting or policy note>"
}}

required_sections keys must be from: abstract, introduction, literature_review, related_work,
materials_and_methods, methodology, results, discussion, conclusion, methods"""

        from langchain_core.messages import SystemMessage, HumanMessage
        try:
            resp = await self.llm.ainvoke([
                SystemMessage(content="You are a precise scientific publishing constraints extractor. Return only valid JSON."),
                HumanMessage(content=prompt),
            ])
            text = resp.content.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            return json.loads(text.strip())
        except Exception as e:
            logger.warning("JournalIntelligence LLM fallback failed", error=str(e))
            return JOURNAL_DB["elsevier"]

    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        journal_type = state.get("journal_type", "elsevier")
        domain = state.get("domain", "")
        preferred_word_count = state.get("preferred_word_count", 0)
        citation_style_override = state.get("citation_style", "")

        constraints = self._lookup_db(journal_type)
        if constraints is None:
            logger.info("Journal not in DB — inferring via LLM", journal=journal_type)
            constraints = await self._infer_constraints(journal_type, domain)

        # Apply user overrides
        if citation_style_override:
            constraints = {**constraints, "citation_style": citation_style_override}
        if preferred_word_count and preferred_word_count > 0:
            # Respect user's target if it's within journal limits
            cap = constraints.get("word_limit", 9000)
            constraints = {**constraints, "word_limit": min(preferred_word_count, cap)}

        constraints["citation_format_description"] = CITATION_FORMAT_MAP.get(
            constraints.get("citation_style", "apa"),
            "APA 7th Edition (Author, Year) in-text; full reference list"
        )

        logger.info(
            "Journal Intelligence initialized",
            journal=journal_type,
            word_limit=constraints.get("word_limit"),
            citation_style=constraints.get("citation_style"),
            figure_limit=constraints.get("figure_limit"),
        )
        return {"journal_constraints": constraints}
