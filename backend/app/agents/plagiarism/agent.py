"""
Plagiarism + AI Detection Engine — Module 5 (ENHANCED)
Similarity scoring, LLM-based perplexity, burstiness, stylometric,
n-gram analysis, entropy, vocabulary richness, coherence scoring.
"""
from __future__ import annotations

import re
import math
import statistics
import hashlib
from collections import Counter
from typing import Dict, Any, List, Tuple
import structlog

from sentence_transformers import SentenceTransformer
import numpy as np
from langchain_core.messages import HumanMessage
import textstat

from app.core.config import settings
from app.core.llm_factory import get_fast_llm

logger = structlog.get_logger()


class PlagiarismAgent:
    EMBED_MODEL = "all-MiniLM-L6-v2"

    def __init__(self):
        self.embedder = SentenceTransformer(self.EMBED_MODEL)
        self.llm = get_fast_llm(max_tokens=2048)

    # ─── Similarity Scoring ────────────────────────────────────────────────

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))

    def _compute_passage_similarity(self, text: str, reference_texts: List[str]) -> float:
        if not reference_texts or not text:
            return 0.0
        doc_emb = self.embedder.encode([text])[0]
        ref_embs = self.embedder.encode(reference_texts)
        sims = [self._cosine_similarity(doc_emb, r) for r in ref_embs]
        return float(max(sims)) * 100.0

    # ─── AI Detection — Perplexity (character entropy) ────────────────────

    def _character_entropy(self, text: str) -> float:
        if not text:
            return 5.0
        freq = Counter(text)
        total = len(text)
        return -sum((c / total) * math.log2(c / total) for c in freq.values())

    # ─── AI Detection — Word-level entropy ────────────────────────────────

    def _word_entropy(self, text: str) -> float:
        words = re.findall(r"\b\w+\b", text.lower())
        if not words:
            return 5.0
        freq = Counter(words)
        total = len(words)
        return -sum((c / total) * math.log2(c / total) for c in freq.values())

    # ─── AI Detection — Burstiness (sentence variance) ────────────────────

    def _burstiness(self, text: str) -> float:
        sentences = re.split(r"(?<=[.!?])\s+", text.strip())
        lengths = [len(s.split()) for s in sentences if len(s.split()) >= 3]
        if len(lengths) < 4:
            return 0.5
        mean = statistics.mean(lengths)
        std = statistics.stdev(lengths)
        if mean == 0:
            return 0.5
        cv = std / mean
        # Human academic text typically CV 0.4–0.8; AI text 0.1–0.3
        return min(cv, 1.5)

    # ─── AI Detection — N-gram Repetition ─────────────────────────────────

    def _ngram_repetition_score(self, text: str, n: int = 4) -> float:
        words = re.findall(r"\b\w+\b", text.lower())
        if len(words) < n:
            return 0.0
        ngrams = [tuple(words[i:i+n]) for i in range(len(words) - n + 1)]
        total = len(ngrams)
        unique = len(set(ngrams))
        return 1.0 - (unique / total) if total > 0 else 0.0

    # ─── AI Detection — Vocabulary Richness (Type-Token Ratio) ────────────

    def _vocabulary_richness(self, text: str) -> float:
        words = re.findall(r"\b[a-z]+\b", text.lower())
        if not words:
            return 0.5
        return len(set(words)) / len(words)

    # ─── AI Detection — Readability Consistency ───────────────────────────

    def _readability_variance(self, text: str) -> float:
        sentences = re.split(r"(?<=[.!?])\s+", text.strip())
        if len(sentences) < 5:
            return 0.5
        scores = []
        for sent in sentences:
            if len(sent.split()) >= 5:
                try:
                    scores.append(textstat.flesch_reading_ease(sent))
                except Exception:
                    pass
        if len(scores) < 3:
            return 0.5
        return statistics.stdev(scores) / max(statistics.mean(scores), 1)

    # ─── AI Detection — Passive Voice Density ─────────────────────────────

    def _passive_voice_density(self, text: str) -> float:
        sentences = re.split(r"(?<=[.!?])\s+", text)
        passive = sum(
            1 for s in sentences
            if re.search(r"\b(is|are|was|were|be|been|being)\s+\w+ed\b", s, re.IGNORECASE)
        )
        return passive / max(len(sentences), 1)

    # ─── AI Detection — Transition Word Density ───────────────────────────

    def _transition_density(self, text: str) -> float:
        AI_TRANSITIONS = [
            "furthermore", "moreover", "additionally", "consequently",
            "in conclusion", "it is worth noting", "it should be noted",
            "it is important", "overall", "in summary", "to summarize",
            "notably", "specifically", "significantly", "importantly",
        ]
        sentences = re.split(r"(?<=[.!?])\s+", text)
        count = sum(
            1 for s in sentences
            if any(t in s.lower() for t in AI_TRANSITIONS)
        )
        return count / max(len(sentences), 1)

    # ─── Combined AI Probability ──────────────────────────────────────────

    def _estimate_ai_probability(self, text: str) -> Dict[str, float]:
        char_entropy = self._character_entropy(text)
        word_entropy = self._word_entropy(text)
        burstiness = self._burstiness(text)
        ngram_rep = self._ngram_repetition_score(text, n=4)
        vocab_richness = self._vocabulary_richness(text)
        transition_dens = self._transition_density(text)
        passive_dens = self._passive_voice_density(text)

        # Score components (0 = more human, 1 = more AI)
        # Low entropy → AI
        entropy_score = max(0.0, (5.5 - char_entropy) / 5.5)
        # Low burstiness → AI (human text is bursty)
        burstiness_score = max(0.0, (0.45 - burstiness) / 0.45) if burstiness < 0.45 else 0.0
        # High ngram repetition → AI
        ngram_score = ngram_rep
        # Low vocab richness → AI
        vocab_score = max(0.0, (0.45 - vocab_richness) / 0.45) if vocab_richness < 0.45 else 0.0
        # High AI-style transitions → AI
        transition_score = min(transition_dens * 3, 1.0)

        # Weighted combination
        raw_ai = (
            entropy_score * 0.20 +
            burstiness_score * 0.25 +
            ngram_score * 0.15 +
            vocab_score * 0.15 +
            transition_score * 0.25
        )
        ai_probability = min(max(raw_ai * 100, 0.0), 100.0)

        return {
            "ai_probability": ai_probability,
            "char_entropy": char_entropy,
            "word_entropy": word_entropy,
            "burstiness": burstiness,
            "ngram_repetition": ngram_rep,
            "vocabulary_richness": vocab_richness,
            "transition_density": transition_dens,
            "passive_voice_density": passive_dens,
        }

    # ─── LLM-Assisted AI Detection ────────────────────────────────────────

    async def llm_ai_detection(self, text_sample: str) -> float:
        """Use Claude to assess whether a text passage reads as AI-generated."""
        message = HumanMessage(
            content=(
                "You are an expert human writing analyst. Assess whether the following academic text "
                "was written by a human researcher or generated by AI.\n\n"
                "Analyze: sentence variation, vocabulary naturalness, argument flow, domain expertise, "
                "stylistic quirks, hedging patterns, and overall authenticity.\n\n"
                "Return ONLY a JSON: {\"ai_probability\": <float 0-100>, \"reasoning\": \"<brief>\"}\n\n"
                f"TEXT SAMPLE:\n{text_sample[:2000]}"
            )
        )
        try:
            import json
            resp = await self.llm.ainvoke([message])
            data = json.loads(resp.content)
            return min(max(float(data.get("ai_probability", 50.0)), 0.0), 100.0)
        except Exception:
            return 50.0

    # ─── Plagiarism Passage Flagging ──────────────────────────────────────

    def _flag_passages(self, paper_sections: Dict, ref_texts: List[str]) -> Dict[str, Any]:
        flagged: Dict[str, Any] = {}
        for section_name, text in paper_sections.items():
            if not text:
                continue
            sentences = re.split(r"(?<=[.!?])\s+", text)
            high_sim = []
            section_max = 0.0
            for sentence in sentences:
                if len(sentence.split()) < 8:
                    continue
                sim = self._compute_passage_similarity(sentence, ref_texts[:30])
                if sim > 65.0:
                    high_sim.append({"sentence": sentence.strip(), "similarity": sim})
                    section_max = max(section_max, sim)
            flagged[section_name] = {
                "text": text,
                "high_similarity_passages": high_sim,
                "max_similarity": section_max,
            }
        return flagged

    def _get_all_text(self, sections: Dict) -> str:
        order = ["abstract", "introduction", "literature_review", "methodology", "results", "discussion", "conclusion"]
        return "\n\n".join(sections.get(s, "") for s in order if sections.get(s))

    # ─── Main Run ─────────────────────────────────────────────────────────

    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        paper_sections = state.get("paper_sections", {})
        references = state.get("references", [])
        full_text = self._get_all_text(paper_sections)

        if not full_text:
            return {"plagiarism_score": 0.0, "ai_detection_score": 0.0, "flagged_sections": paper_sections}

        # Reference texts for similarity comparison
        def extract_text(val) -> str:
            if isinstance(val, str):
                return val
            elif isinstance(val, dict):
                return " ".join(extract_text(v) for v in val.values())
            elif isinstance(val, list):
                return " ".join(extract_text(v) for v in val)
            else:
                return str(val) if val is not None else ""

        ref_texts = []
        for r in references:
            if not r.get("title"):
                continue
            abs_val = r.get("abstract")
            abs_str = extract_text(abs_val)
            
            final_text = abs_str if abs_str.strip() else r.get("title", "")
            if isinstance(final_text, str) and final_text.strip():
                ref_texts.append(final_text)

        # Heuristic AI detection
        ai_metrics = self._estimate_ai_probability(full_text)
        heuristic_ai_score = ai_metrics["ai_probability"]

        # LLM AI detection (sample from abstract + methodology)
        sample = (paper_sections.get("abstract", "") + "\n\n" + paper_sections.get("methodology", ""))[:2500]
        llm_ai_score = await self.llm_ai_detection(sample)

        # Combined AI score (weighted average: heuristic 40%, LLM 60%)
        combined_ai_score = heuristic_ai_score * 0.4 + llm_ai_score * 0.6

        # Plagiarism: similarity to references
        plagiarism_score = self._compute_passage_similarity(full_text[:3000], ref_texts) if ref_texts else 5.0

        # Stylometric metrics
        style_metrics = {
            "vocabulary_richness": ai_metrics["vocabulary_richness"],
            "burstiness": ai_metrics["burstiness"],
            "passive_voice_density": ai_metrics["passive_voice_density"],
            "transition_density": ai_metrics["transition_density"],
            "ngram_repetition": ai_metrics["ngram_repetition"],
            "flesch_reading_ease": textstat.flesch_reading_ease(full_text[:2000]),
            "gunning_fog": textstat.gunning_fog(full_text[:2000]),
        }

        # Passage flagging
        flagged_data = self._flag_passages(paper_sections, ref_texts)
        flagged_sections = {k: v["text"] for k, v in flagged_data.items()}

        logger.info(
            "Plagiarism + AI detection complete",
            plagiarism=plagiarism_score,
            ai_heuristic=heuristic_ai_score,
            ai_llm=llm_ai_score,
            ai_combined=combined_ai_score,
        )

        return {
            "plagiarism_score": min(plagiarism_score, 100.0),
            "ai_detection_score": combined_ai_score,
            "flagged_sections": flagged_sections,
            "ai_metrics": ai_metrics,
            "style_metrics": style_metrics,
            "flagged_passages": {k: v["high_similarity_passages"] for k, v in flagged_data.items()},
            "heuristic_ai_score": heuristic_ai_score,
            "llm_ai_score": llm_ai_score,
        }
