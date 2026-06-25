"""
Humanization Engine — Module 6 (ITERATIVE: rewrites until AI < 5%)
Each section rewritten independently; re-scored after each pass.
"""
from __future__ import annotations

import asyncio
import re
import math
import statistics
from typing import Dict, Any, List, Optional
import structlog

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import SystemMessage, HumanMessage

from app.core.config import settings
from app.core.llm_factory import get_writing_llm

logger = structlog.get_logger()

SYSTEM_HUMANIZE = """You are a senior professor and scientific editor who has published over 200 papers in top-tier SCI journals.

Rewrite the following text so it reads as if written by you — a human domain expert with deep intuition, natural academic voice, and scholarly precision.

Strict rules:
1. NEVER alter any factual claims, statistics, or findings
2. NEVER remove or modify citation numbers [1], [2], etc.
3. NEVER simplify technical terminology — keep it precise
4. Vary sentence structure naturally: mix short punchy sentences with longer analytical ones
5. Use discipline-specific vocabulary as a genuine expert would
6. Add natural hedging: "appears to", "suggests that", "it is argued that"
7. Include occasional first-plural "we" for methodology sections only
8. Use active/passive voice mix as real papers do (not uniformly passive)
9. Do NOT use AI-favoured filler phrases: "Furthermore,", "Moreover,", "It is worth noting", "Significantly,"
10. Target same word count ±10%

Return ONLY the rewritten text. No preamble. No explanation."""

SYSTEM_SECTION_SPECIFIC = {
    "abstract": "Write as a 250-word structured abstract: Background (1 sentence), Objective (1 sentence), Methods (2 sentences), Results (2 sentences), Conclusion (1 sentence). Be precise and impactful.",
    "introduction": "Write with a narrative arc: broad problem → specific gap → your contribution → paper structure. Use citations naturally. Strong opening sentence that grabs attention.",
    "literature_review": "Write as critical analysis — not just summarising but evaluating, contrasting, and positioning. Group papers thematically. Identify clear gaps your work addresses.",
    "methodology": "Write with reproducibility in mind. Step-by-step, precise, use passive voice where appropriate. Include justification for design choices.",
    "results": "Present findings objectively. Reference figures/tables by number. State statistical significance. Use hedged language for interpretations.",
    "discussion": "Interpret findings in context of literature. Acknowledge limitations honestly. Compare with prior work. Future directions should be specific.",
    "conclusion": "Synthesise key contributions concisely. Practical implications. One specific future research direction.",
}


class HumanizationAgent:
    MAX_PASSES = 3
    TARGET_AI_SCORE = 4.0

    def __init__(self):
        self.llm = get_writing_llm(max_tokens=8192)

    def _quick_ai_score(self, text: str) -> float:
        """Full 7-signal heuristic AI score — same signals as PlagiarismAgent for consistency."""
        if not text or len(text.split()) < 20:
            return 0.0
        sentences = re.split(r"(?<=[.!?])\s+", text.strip())
        lengths = [len(s.split()) for s in sentences if len(s.split()) >= 3]

        # Signal 1: Burstiness (sentence length variance — low = AI)
        if len(lengths) >= 4:
            cv = statistics.stdev(lengths) / max(statistics.mean(lengths), 1)
            burstiness_score = max(0.0, (0.45 - cv) / 0.45) if cv < 0.45 else 0.0
        else:
            burstiness_score = 0.3

        # Signal 2: AI transition words density
        AI_TRANSITIONS = [
            "furthermore", "moreover", "additionally", "consequently",
            "in conclusion", "it is worth noting", "it should be noted",
            "it is important", "overall", "in summary", "to summarize",
            "notably", "specifically", "significantly", "importantly",
        ]
        transition_count = sum(1 for s in sentences if any(t in s.lower() for t in AI_TRANSITIONS))
        transition_score = min((transition_count / max(len(sentences), 1)) * 3, 1.0)

        # Signal 3: N-gram repetition (4-gram)
        words = re.findall(r"\b\w+\b", text.lower())
        if len(words) >= 4:
            ngrams = [tuple(words[i:i+4]) for i in range(len(words) - 3)]
            ngram_score = 1.0 - (len(set(ngrams)) / max(len(ngrams), 1))
        else:
            ngram_score = 0.0

        # Signal 4: Vocabulary richness (TTR — low = AI)
        if words:
            ttr = len(set(words)) / len(words)
            vocab_score = max(0.0, (0.45 - ttr) / 0.45) if ttr < 0.45 else 0.0
        else:
            vocab_score = 0.0

        # Signal 5: Character entropy (low = AI)
        if text:
            from collections import Counter as _Counter
            import math as _math
            freq = _Counter(text)
            total = len(text)
            char_entropy = -sum((c / total) * _math.log2(c / total) for c in freq.values())
            entropy_score = max(0.0, (5.5 - char_entropy) / 5.5)
        else:
            entropy_score = 0.5

        # Signal 6: Passive voice density
        passive_count = sum(
            1 for s in sentences
            if re.search(r"\b(is|are|was|were|be|been|being)\s+\w+ed\b", s, re.IGNORECASE)
        )
        passive_density = passive_count / max(len(sentences), 1)
        # Very high passive = AI (>0.7 is suspect)
        passive_score = max(0.0, (passive_density - 0.5) / 0.5) if passive_density > 0.5 else 0.0

        # Signal 7: Sentence length uniformity (low std dev = AI)
        if len(lengths) >= 3:
            uniformity = 1.0 - min(statistics.stdev(lengths) / max(statistics.mean(lengths), 1), 1.0)
            uniformity_score = uniformity * 0.5
        else:
            uniformity_score = 0.3

        raw = (
            entropy_score     * 0.15 +
            burstiness_score  * 0.22 +
            ngram_score       * 0.13 +
            vocab_score       * 0.13 +
            transition_score  * 0.22 +
            passive_score     * 0.08 +
            uniformity_score  * 0.07
        )
        return min(max(raw * 100, 0.0), 100.0)

    async def _humanize_section(
        self, section_name: str, text: str, writing_tone: str, pass_num: int, repair_instruction: str = ""
    ) -> str:
        if not text or len(text.split()) < 15:
            return text

        section_extra = SYSTEM_SECTION_SPECIFIC.get(section_name, "")
        tone_note = f"This is a {writing_tone} paper. " if writing_tone != "academic" else ""
        pass_note = f"[PASS {pass_num}/{self.MAX_PASSES} — make it more natural than the previous version]" if pass_num > 1 else ""
        
        repair_note = ""
        if repair_instruction:
            repair_note = f"\n\nURGENT REPAIR INSTRUCTIONS FROM EDITOR:\n{repair_instruction}\nYou must prioritize fixing these issues in your rewrite."

        messages = [
            SystemMessage(content=f"{SYSTEM_HUMANIZE}\n\n{tone_note}{section_extra}{repair_note}"),
            HumanMessage(content=f"{pass_note}\n\n{text}"),
        ]
        chain = self.llm | StrOutputParser()
        try:
            return await chain.ainvoke(messages)
        except Exception as e:
            logger.error("Section humanization failed", section=section_name, pass_num=pass_num, error=str(e))
            return text

    async def _humanize_all_sections_once(
        self, sections: Dict[str, str], writing_tone: str, pass_num: int, repair_instruction: str = ""
    ) -> Dict[str, str]:
        """Humanize all sections in parallel (2 at a time to respect rate limits)."""
        section_keys = [
            "abstract", "introduction", "literature_review",
            "methodology", "results", "discussion", "conclusion"
        ]
        result = dict(sections)
        # Process in batches of 2
        for i in range(0, len(section_keys), 2):
            batch = [k for k in section_keys[i:i+2] if sections.get(k)]
            if not batch:
                continue
            tasks = [
                self._humanize_section(k, sections[k], writing_tone, pass_num, repair_instruction)
                for k in batch
            ]
            outputs = await asyncio.gather(*tasks, return_exceptions=True)
            for key, output in zip(batch, outputs):
                if isinstance(output, str) and len(output) > 50:
                    result[key] = output
        return result

    def _estimate_combined_ai_score(self, sections: Dict[str, str]) -> float:
        all_text = " ".join(v for v in sections.values() if v)
        if not all_text:
            return 0.0
        return self._quick_ai_score(all_text)

    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        paper_sections = state.get("paper_sections", {})
        current_ai_score = state.get("ai_detection_score", 100.0)
        writing_tone = state.get("writing_tone", "academic")
        repair_jobs = state.get("repair_jobs", [])
        
        # Extract specific instructions for humanize (which could include plagiarism fixes)
        humanize_repairs = [j for j in repair_jobs if j.get("agent") == "humanize"]
        repair_instruction = "\n".join(j.get("instruction", "") for j in humanize_repairs)
        
        needs_repair = len(humanize_repairs) > 0

        if current_ai_score <= self.TARGET_AI_SCORE and not needs_repair:
            logger.info("AI score already below target and no repairs needed — skipping humanization", score=current_ai_score)
            return {"humanized_sections": paper_sections, "new_ai_score": current_ai_score}

        humanized = dict(paper_sections)
        ai_score = current_ai_score

        for pass_num in range(1, self.MAX_PASSES + 1):
            logger.info("Humanization pass", pass_num=pass_num, ai_score=ai_score)
            humanized = await self._humanize_all_sections_once(humanized, writing_tone, pass_num, repair_instruction)
            ai_score = self._estimate_combined_ai_score(humanized)
            logger.info("Post-humanization AI estimate", pass_num=pass_num, ai_score=ai_score)
            
            # If we were explicitly asked to repair plagiarism, we should probably do all passes, 
            # or at least not break early just because AI score is low.
            if ai_score <= self.TARGET_AI_SCORE and not needs_repair:
                logger.info("AI score target achieved", pass_num=pass_num, ai_score=ai_score)
                break

        # Final conservative floor — never claim 0%
        final_ai_score = max(ai_score, 1.5)

        logger.info(
            "Humanization complete",
            passes=pass_num,
            initial_ai=current_ai_score,
            final_ai=final_ai_score,
        )

        return {
            "humanized_sections": humanized,
            "new_ai_score": final_ai_score,
        }
