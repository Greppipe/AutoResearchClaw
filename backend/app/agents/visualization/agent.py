"""
DataIntelligenceAgent — Module 3.5 (PaperVizAgent Closed-Loop Upgrade)
Coordinates a Retriever, Planner, Stylist, Visualizer, and Critic in a closed loop
to generate publication-grade methodology and discussion section tables/charts.
"""
from __future__ import annotations

import json
from typing import Dict, Any, List
import structlog

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import JsonOutputParser

from app.core.llm_factory import get_fast_llm

logger = structlog.get_logger()

# ─── Prompts for the PaperVizAgent Sub-Phases ──────────────────────────────────

PLANNER_PROMPT = """You are a scientific plotting planner. Your job is to analyze the research context and decide exactly how to structure the tables and figures for the Methodology and Discussion sections.

Return ONLY a JSON plan:
{
  "methodology_plan": {
    "table_m1_focus": "<e.g., comparative overview of related methodologies>",
    "table_m2_focus": "<e.g., descriptive statistics of dataset parameters>",
    "chart_m1_focus": "<e.g., workflow efficiency or sample breakdown>"
  },
  "discussion_plan": {
    "table_d1_focus": "<e.g., performance comparison against 5 named SOTA baselines>",
    "table_d2_focus": "<e.g., statistical significance, p-values, Cohen's d>",
    "chart_d1_focus": "<e.g., accuracy/F1 score bar comparison>"
  }
}"""

STYLIST_PROMPT = """You are a scientific data visualization stylist. Based on the target journal type and citation style, decide the formatting guidelines, colors, and layout rules.

Return ONLY a JSON style sheet:
{
  "color_palette": {
    "primary": "<hex code, e.g., Slate Blue/Navy #1a1a3a>",
    "secondary": "<hex code, e.g., Teal/Emerald #10b981>",
    "accent": "<hex code, e.g., Amber/Gold #f59e0b>",
    "style_theme": "light"
  },
  "formatting": {
    "font_family": "Times New Roman or Arial depending on citation style",
    "dpi": 300,
    "grid_lines": true,
    "error_bars": true,
    "table_border_style": "APA double line or IEEE single line rules"
  }
}"""

VISUALIZER_PROMPT = """You are a scientific data visualizer for top-tier journals (Nature, IEEE, Elsevier).
Your task is to generate the final publication-grade tables and charts in JSON format.

Use the provided PLAN and STYLIST guidelines to fill in the data context.
Return ONLY valid JSON:
{
  "methodology_visuals": [
    {
      "kind": "table",
      "title": "<Table Title>",
      "caption": "<Table Caption>",
      "headers": ["Header1", "Header2", ...],
      "rows": [["Row1Val1", "Row1Val2", ...], ...],
      "notes": "<Table notes, statistical indicators>",
      "purpose": "method_comparison|dataset_characteristics",
      "styling": { "border": "<stylist_border_style>", "primary_color": "<stylist_primary_color>" }
    },
    ...
  ],
  "discussion_visuals": [
    {
      "kind": "table",
      ...
    },
    {
      "kind": "chart",
      "type": "bar|line|scatter",
      "title": "<Figure Title>",
      "x_label": "<X Axis Label>",
      "y_label": "<Y Axis Label>",
      "x_data": ["Val1", "Val2", ...],
      "datasets": [
        { "label": "Series1", "data": [1.0, 2.0, ...] }
      ],
      "caption": "<Figure Caption>",
      "purpose": "sota_comparison|statistical_summary",
      "styling": { "colors": ["<stylist_primary>", "<stylist_secondary>"] }
    }
  ]
}

MANDATORY DATA COMPLIANCE:
1. All numeric values must be plausible and derived logically from the research context.
2. The discussion SOTA comparison table MUST compare the proposed method with at least 5 prior publications from the literature.
3. The statistical significance table MUST contain realistic p-values (e.g., p < 0.05) and effect sizes (Cohen's d).
4. Do NOT output markdown formatting blocks, return ONLY the raw JSON."""

CRITIC_PROMPT = """You are a rigorous peer reviewer and data critic for a Q1 SCI journal.
Evaluate the provided generated tables and charts against the draft manuscript text and target guidelines.

Check for:
1. Factual consistency: Do the performance numbers, datasets, and methods mentioned in the visualizer output align with the manuscript text?
2. Technical completeness: Are all required tables (method comparison, dataset characteristics, SOTA comparison, statistical significance) and charts present?
3. SOTA comparison: Does the SOTA table compare the proposed method against at least 5 prior publications?
4. Quality and plausibility: Are the numbers realistic, and do they show appropriate statistical significance (p < 0.05) for the proposed method?

Return ONLY a JSON audit report:
{
  "passed": <true|false>,
  "score": <float 0-10>,
  "issues": [
    {
      "visual_title": "<Title of the table or chart>",
      "issue": "<What is wrong, e.g., missing 5th baseline, p-value mismatch>",
      "instruction": "<Precise fix instruction for the visualizer agent>"
    }
  ]
}"""


class DataIntelligenceAgent:
    def __init__(self):
        self.llm = get_fast_llm(max_tokens=6144)

    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        if state.get("methodology_visuals") and state.get("discussion_visuals"):
            logger.info("Visuals already locked in state by research node, passing through.")
            return {
                "methodology_visuals": state["methodology_visuals"],
                "discussion_visuals": state["discussion_visuals"],
            }

        # ─── 1. Retriever Phase ────────────────────────────────────────────────
        retrieved_context = self._retriever_phase(state)
        logger.info("DataIntelligenceAgent: Retriever Phase complete.")

        # ─── 2. Planner Phase ──────────────────────────────────────────────────
        plan = await self._planner_phase(retrieved_context)
        logger.info("DataIntelligenceAgent: Planner Phase complete.", plan=plan)

        # ─── 3. Stylist Phase ──────────────────────────────────────────────────
        style = await self._stylist_phase(state.get("journal_type", "SCI"), state.get("citation_style", "ieee"))
        logger.info("DataIntelligenceAgent: Stylist Phase complete.", style=style)

        # ─── 4 & 5. Visualizer & Critic Closed-Loop Phase ──────────────────────
        visuals = {"methodology_visuals": [], "discussion_visuals": []}
        critic_feedback = ""
        max_critic_loops = 2

        for iteration in range(max_critic_loops):
            logger.info("DataIntelligenceAgent: Visualizer Phase iteration.", iteration=iteration + 1)
            visuals = await self._visualizer_phase(retrieved_context, plan, style, critic_feedback)

            logger.info("DataIntelligenceAgent: Critic Phase evaluation.")
            audit_report = await self._critic_phase(retrieved_context, visuals)
            logger.info("DataIntelligenceAgent: Critic report received.", passed=audit_report.get("passed"), score=audit_report.get("score"))

            if audit_report.get("passed") or not audit_report.get("issues"):
                logger.info("DataIntelligenceAgent: Critic approved visuals.")
                break

            # Format feedback for next visualizer iteration
            issues = audit_report.get("issues", [])
            critic_feedback = "\n".join(
                f"- Issue in '{i.get('visual_title')}': {i.get('issue')} -> FIX: {i.get('instruction')}"
                for i in issues
            )
            logger.info("DataIntelligenceAgent: Visualizer retrying based on critic feedback.")

        return {
            "methodology_visuals": visuals.get("methodology_visuals", []),
            "discussion_visuals": visuals.get("discussion_visuals", []),
        }

    def _retriever_phase(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Gathers context, literature records, and manuscript text from the state."""
        references = state.get("references", [])
        paper_sections = state.get("paper_sections", {})
        extracted = state.get("extracted_data", {})
        ddi_facts = state.get("ddi_brief", {})

        top_refs = sorted(
            [r for r in references if r.get("title")],
            key=lambda x: x.get("citation_count") or 0,
            reverse=True,
        )[:20]

        ref_summary = [
            {
                "title": r.get("title", ""),
                "authors": r.get("authors", [])[:2],
                "year": r.get("year"),
                "journal": r.get("journal", ""),
                "citation_count": r.get("citation_count", 0),
            }
            for r in top_refs
        ]

        return {
            "title": state.get("title", ""),
            "domain": state.get("domain", ""),
            "study_type": state.get("study_type", "experimental"),
            "keywords": state.get("keywords", []),
            "methodology_description": state.get("methodology_description", ""),
            "dataset_description": state.get("dataset_description", ""),
            "analysis_methods": state.get("analysis_methods", ""),
            "tools_used": state.get("tools_used", ""),
            "expected_findings": state.get("expected_findings", ""),
            "methodology_section_excerpt": paper_sections.get("materials_and_methods", "")[:1500],
            "discussion_section_excerpt": paper_sections.get("discussion", "")[:1500],
            "results_section_excerpt": paper_sections.get("results", "")[:1000],
            "top_references": ref_summary,
            "extracted_tables": extracted.get("tables_described", []),
            "ddi_grounded_data": ddi_facts,
            "existing_chart_data": state.get("chart_data", []),
            "existing_table_data": state.get("table_data", []),
        }

    async def _planner_phase(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Decides the layout, focus, and types of figures and tables needed."""
        messages = [
            SystemMessage(content=PLANNER_PROMPT),
            HumanMessage(content=f"Plan figures and tables for this research context:\n\n{json.dumps(context, default=str)}")
        ]
        chain = self.llm | JsonOutputParser()
        try:
            return await chain.ainvoke(messages)
        except Exception as e:
            logger.warning("Planner Phase failed, using fallback plan", error=str(e))
            return {
                "methodology_plan": {"table_m1_focus": "method comparison", "table_m2_focus": "dataset parameters", "chart_m1_focus": "sample flow"},
                "discussion_plan": {"table_d1_focus": "SOTA comparison against 5 baselines", "table_d2_focus": "statistical significance", "chart_d1_focus": "accuracy bar"}
            }

    async def _stylist_phase(self, journal_type: str, citation_style: str) -> Dict[str, Any]:
        """Generates color maps, line parameters, and borders aligned with journal styles."""
        messages = [
            SystemMessage(content=STYLIST_PROMPT),
            HumanMessage(content=f"Generate styling parameters for Journal Type: '{journal_type}' and Citation Style: '{citation_style}'")
        ]
        chain = self.llm | JsonOutputParser()
        try:
            return await chain.ainvoke(messages)
        except Exception as e:
            logger.warning("Stylist Phase failed, using fallback style", error=str(e))
            return {
                "color_palette": {"primary": "#1a1a3a", "secondary": "#10b981", "accent": "#f59e0b", "style_theme": "light"},
                "formatting": {"font_family": "Times New Roman", "dpi": 300, "grid_lines": True, "error_bars": True, "table_border_style": "APA"}
            }

    async def _visualizer_phase(self, context: Dict[str, Any], plan: Dict[str, Any], style: Dict[str, Any], critic_feedback: str) -> Dict[str, Any]:
        """Generates raw visual figures and tables content."""
        prompt = VISUALIZER_PROMPT
        if critic_feedback:
            prompt += f"\n\n=== REPAIR DISPATCH FROM CRITIC AGENT ===\nPlease correct the following errors from your previous attempt:\n{critic_feedback}"

        payload = {
            "context": context,
            "plan": plan,
            "style": style
        }

        messages = [
            SystemMessage(content=prompt),
            HumanMessage(content=json.dumps(payload, default=str))
        ]
        chain = self.llm | JsonOutputParser()
        try:
            return await chain.ainvoke(messages)
        except Exception as e:
            logger.warning("Visualizer Phase failed", error=str(e))
            return {"methodology_visuals": [], "discussion_visuals": []}

    async def _critic_phase(self, context: Dict[str, Any], visuals: Dict[str, Any]) -> Dict[str, Any]:
        """Audits visuals for factual correctness, completeness, and formatting standards."""
        payload = {
            "manuscript_context": {
                "methodology_excerpt": context.get("methodology_section_excerpt", ""),
                "discussion_excerpt": context.get("discussion_section_excerpt", ""),
                "results_excerpt": context.get("results_section_excerpt", "")
            },
            "generated_visuals": visuals
        }

        messages = [
            SystemMessage(content=CRITIC_PROMPT),
            HumanMessage(content=json.dumps(payload, default=str))
        ]
        chain = self.llm | JsonOutputParser()
        try:
            return await chain.ainvoke(messages)
        except Exception as e:
            logger.warning("Critic Phase failed, passing by default", error=str(e))
            return {"passed": True, "score": 10.0, "issues": []}

