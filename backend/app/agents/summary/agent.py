"""
Research Summary Agent — Mode 2
Generates a structured research summary (not a full paper).
Output sections: Executive Summary, Key Findings, Methodology, Gap & Contribution,
                 Limitations, Future Work, Key References.
"""
from __future__ import annotations

import asyncio
import json
from typing import Dict, Any, List
import structlog

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from app.core.llm_factory import get_writing_llm

logger = structlog.get_logger()

SUMMARY_SYSTEM = """You are a scientific research analyst and science communicator.
Generate a comprehensive, accurate research summary from the provided research context and document analysis.

Return ONLY valid JSON with this structure:
{
  "executive_summary": "<200-300 word plain-language overview for a non-specialist audience. What was done, why it matters, what was found.>",

  "research_background": "<2-3 paragraphs on the research domain, why this problem is important, and the current state of knowledge.>",

  "key_findings": [
    "<Finding 1 with specific numbers and statistics>",
    "<Finding 2>",
    "<Finding 3>",
    "<Finding 4>",
    "<Finding 5>"
  ],

  "methodology_overview": "<2 paragraphs: what was done and how. Include specific methods, tools, dataset sizes.>",

  "research_gap_and_contribution": "<What gap existed, what this work contributes, why it is significant.>",

  "limitations": [
    "<Limitation 1>",
    "<Limitation 2>",
    "<Limitation 3>"
  ],

  "future_work": [
    "<Future direction 1 — specific and actionable>",
    "<Future direction 2>",
    "<Future direction 3>"
  ],

  "key_statistics": [
    {"metric": "<name>", "value": "<value>", "context": "<what it means>"}
  ],

  "glossary": [
    {"term": "<key technical term>", "definition": "<plain-language definition>"}
  ],

  "impact_statement": "<1 paragraph on the broader societal, clinical, or technological impact if successful.>",

  "one_sentence_summary": "<The entire research distilled into one clear sentence.>"
}

Rules:
- Prioritise facts from DDI brief (document-grounded) over general knowledge
- If DDI brief has specific numbers, use them exactly
- Do NOT fabricate statistics — mark uncertain values with 'approx.'
- Return ONLY valid JSON"""


class SummaryAgent:
    def __init__(self):
        self.llm = get_writing_llm(max_tokens=6000)

    async def run(self, state: Dict[str, Any], ddi_brief: Dict[str, str]) -> Dict[str, Any]:
        ddi_text = "\n\n".join(
            f"[{k.upper().replace('_', ' ')}]\n{v}"
            for k, v in ddi_brief.items()
            if v and v != "Not found in documents"
        )

        refs = state.get("references", [])
        ref_list = "\n".join(
            f"{i+1}. {r.get('title', '')} — {', '.join(str(a) for a in r.get('authors', [])[:2])} ({r.get('year', '')})"
            for i, r in enumerate(refs[:20])
        )

        human_payload = json.dumps({
            "title": state.get("title", ""),
            "domain": state.get("domain", ""),
            "keywords": state.get("keywords", []),
            "study_type": state.get("study_type", ""),
            "problem_statement": state.get("problem_statement", ""),
            "hypothesis": state.get("hypothesis", ""),
            "objectives": state.get("objectives", ""),
            "novel_contribution": state.get("novel_contribution", ""),
            "author_name": state.get("author_name", ""),
            "ddi_brief": ddi_text[:8000],
            "key_references": ref_list,
        })

        messages = [
            SystemMessage(content=SUMMARY_SYSTEM),
            HumanMessage(content=human_payload),
        ]
        chain = self.llm | JsonOutputParser()

        try:
            result = await chain.ainvoke(messages)
            return result
        except Exception as e:
            logger.error("Summary generation failed", error=str(e))
            return {
                "one_sentence_summary": f"Research on {state.get('title', 'unknown topic')}",
                "executive_summary": "Summary generation encountered an error. Please retry.",
                "key_findings": [],
                "methodology_overview": "",
                "research_gap_and_contribution": "",
                "limitations": [],
                "future_work": [],
                "key_statistics": [],
                "glossary": [],
                "impact_statement": "",
            }
