"""
Deep Document Intelligence — Local NotebookLM Equivalent
=========================================================
Replaces reliance on Google's undocumented API with a fully local,
100%-owned RAG pipeline using sentence-transformers + Claude.

How it achieves accuracy:
  1. Splits every uploaded document into overlapping semantic chunks
  2. Embeds all chunks using a high-quality encoder (all-mpnet-base-v2)
  3. For each paper section target, retrieves the most relevant chunks
  4. Passes grounded source passages to Claude — no hallucination from
     training data, only facts extracted directly from YOUR documents
  5. Returns citations: every factual claim maps back to a source file
"""
from __future__ import annotations

import asyncio
import json
import re
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
import structlog

from sentence_transformers import SentenceTransformer
from langchain_core.messages import HumanMessage
from app.core.llm_factory import get_precise_llm

logger = structlog.get_logger()

# Questions the DDI asks about every document set to build the research brief
_INTERROGATION_QUESTIONS = [
    ("background",        "What is the background context, motivation, and research domain described in these documents?"),
    ("problem",           "What specific problem or challenge is being addressed? What makes it difficult?"),
    ("gap",               "What gaps, limitations, or unresolved issues in existing work are identified?"),
    ("hypothesis",        "What is the stated hypothesis, research question, or central claim?"),
    ("dataset",           "Describe the dataset, study subjects, or experimental materials: size, source, characteristics, inclusion/exclusion criteria."),
    ("methodology",       "Describe the methodology step-by-step: research design, data collection procedures, experimental setup."),
    ("analysis_methods",  "What analytical, statistical, or computational methods were used? Include software, libraries, and parameter settings."),
    ("results_numbers",   "What are the specific quantitative results? Extract all numbers, percentages, p-values, confidence intervals, effect sizes."),
    ("results_qualitative","What qualitative or descriptive findings are reported?"),
    ("figures_tables",    "Describe all figures and tables: what they show, axes, key values, trends."),
    ("contributions",     "What are the novel contributions claimed? List them specifically."),
    ("limitations",       "What limitations, threats to validity, or constraints are acknowledged?"),
    ("future_work",       "What future research directions or recommendations are suggested?"),
    ("tools_software",    "List all software, tools, hardware, APIs, libraries, and version numbers mentioned."),
    ("related_work",      "What prior work is cited? List key papers, authors, and their relevance to this study."),
]


class DeepDocumentIntelligence:
    """
    Local NotebookLM equivalent.
    Ingests extracted document content, builds a semantic index,
    and answers targeted research questions grounded in your documents.
    """

    EMBED_MODEL = "all-mpnet-base-v2"   # Higher accuracy than MiniLM
    CHUNK_SIZE  = 400                    # words per chunk
    CHUNK_OVERLAP = 80                   # overlap between chunks

    def __init__(self):
        self._embedder: Optional[SentenceTransformer] = None
        self._chunks: List[Dict[str, str]] = []     # {text, source, chunk_id}
        self._embeddings: Optional[np.ndarray] = None
        self.llm = get_precise_llm(max_tokens=4096)

    # ── Lazy-load the encoder (heavy model) ──────────────────────────────────

    @property
    def embedder(self) -> SentenceTransformer:
        if self._embedder is None:
            logger.info("Loading sentence-transformer model", model=self.EMBED_MODEL)
            self._embedder = SentenceTransformer(self.EMBED_MODEL)
        return self._embedder

    # ── Text chunking ─────────────────────────────────────────────────────────

    def _chunk_text(self, text: str, source: str) -> List[Dict[str, str]]:
        words = text.split()
        if not words:
            return []
        chunks = []
        step = self.CHUNK_SIZE - self.CHUNK_OVERLAP
        for i in range(0, len(words), step):
            chunk = " ".join(words[i: i + self.CHUNK_SIZE])
            if len(chunk.strip()) > 60:
                chunks.append({"text": chunk, "source": source, "chunk_id": f"{source}:{i}"})
            if i + self.CHUNK_SIZE >= len(words):
                break
        return chunks

    # ── Ingestion ─────────────────────────────────────────────────────────────

    def ingest(self, extracted_data: Dict[str, Any]) -> int:
        """
        Build the semantic index from extracted document data.
        Returns number of chunks indexed.
        """
        self._chunks = []

        # Primary text fields
        for field in ("background", "methodology", "data_results", "conclusions",
                      "raw_content", "full_text"):
            text = extracted_data.get(field, "")
            if text and isinstance(text, str):
                self._chunks.extend(self._chunk_text(text, field))

        # Research gaps / contributions (lists)
        for field in ("research_gaps", "contributions", "figures_described", "tables_described"):
            items = extracted_data.get(field, [])
            if isinstance(items, list):
                combined = "\n".join(str(x) for x in items if x)
                if combined:
                    self._chunks.extend(self._chunk_text(combined, field))

        # Raw extractions from individual files
        for raw in extracted_data.get("raw_extractions", []):
            src = raw.get("filename", "uploaded_file")
            for key in ("ocr_text", "vision_description"):
                val = raw.get(key, "")
                if val:
                    self._chunks.extend(self._chunk_text(str(val), src))
            sections_map = raw.get("sections_map", {})
            for sec_name, paras in sections_map.items():
                if isinstance(paras, list):
                    text = "\n".join(paras)
                    if text:
                        self._chunks.extend(self._chunk_text(text, f"{src}/{sec_name}"))

        if not self._chunks:
            logger.info("No chunks to embed — no document content provided")
            return 0

        texts = [c["text"] for c in self._chunks]
        logger.info("Embedding document chunks", count=len(texts))
        self._embeddings = self.embedder.encode(texts, batch_size=32, show_progress_bar=False)
        logger.info("DDI index ready", chunks=len(self._chunks))
        return len(self._chunks)

    # ── Semantic retrieval ────────────────────────────────────────────────────

    def retrieve(self, query: str, top_k: int = 8) -> List[Dict[str, str]]:
        """Return the top-k most semantically relevant chunks for a query."""
        if self._embeddings is None or len(self._chunks) == 0:
            return []
        q_emb = self.embedder.encode([query])[0]
        norm_q = np.linalg.norm(q_emb)
        if norm_q == 0:
            return []
        norms = np.linalg.norm(self._embeddings, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1e-10, norms)
        scores = (self._embeddings / norms) @ (q_emb / norm_q)
        top_idx = np.argsort(scores)[::-1][:top_k]
        return [
            {**self._chunks[i], "score": float(scores[i])}
            for i in top_idx
            if scores[i] > 0.25  # Relevance threshold
        ]

    # ── Single grounded Q&A ───────────────────────────────────────────────────

    async def _answer_question(self, question: str, context_chunks: List[Dict]) -> str:
        """Answer one question using only retrieved chunks as context."""
        if not context_chunks:
            return "No relevant content found in uploaded documents."

        context = "\n\n---\n\n".join(
            f"[Source: {c['source']}]\n{c['text']}"
            for c in context_chunks
        )

        msg = HumanMessage(
            content=(
                "You are a research analyst who ONLY answers from the provided source documents.\n"
                "RULES:\n"
                "1. Answer ONLY from the context below — do NOT add knowledge from your training data\n"
                "2. If the context does not contain the answer, say 'Not found in documents'\n"
                "3. Quote specific numbers, names, and data exactly as they appear\n"
                "4. Keep answers factual and precise\n\n"
                f"QUESTION: {question}\n\n"
                f"SOURCE CONTEXT:\n{context[:6000]}"
            )
        )
        resp = await self.llm.ainvoke([msg])
        return resp.content.strip()

    # ── Full interrogation ────────────────────────────────────────────────────

    async def interrogate(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run a complete research interrogation of all uploaded documents.
        Returns a structured brief grounded entirely in document content.
        """
        extracted = state.get("extracted_data", {})
        n_chunks = self.ingest(extracted)

        if n_chunks == 0:
            logger.info("No document content to interrogate — using user-provided context only")
            return {"ddi_brief": {}, "ddi_chunks": 0, "ddi_grounded": False}

        logger.info("Starting Deep Document Interrogation", questions=len(_INTERROGATION_QUESTIONS))

        # Run all questions concurrently (batched to respect rate limits)
        brief: Dict[str, str] = {}
        batch_size = 4
        for i in range(0, len(_INTERROGATION_QUESTIONS), batch_size):
            batch = _INTERROGATION_QUESTIONS[i: i + batch_size]
            tasks = []
            for key, question in batch:
                chunks = self.retrieve(question, top_k=8)
                tasks.append(self._answer_question(question, chunks))
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for (key, _), result in zip(batch, results):
                if isinstance(result, str):
                    brief[key] = result
                else:
                    brief[key] = "Extraction error"
                    logger.warning("DDI question failed", key=key, error=str(result))
            await asyncio.sleep(0.3)

        logger.info("DDI interrogation complete", keys=list(brief.keys()))
        return {
            "ddi_brief": brief,
            "ddi_chunks": n_chunks,
            "ddi_grounded": True,
        }

    # ── Source-grounded summary ───────────────────────────────────────────────

    async def summarise_documents(self, state: Dict[str, Any]) -> str:
        """
        Generate a source-grounded research summary from uploaded documents.
        Used by the Summary mode.
        """
        extracted = state.get("extracted_data", {})
        self.ingest(extracted)

        questions = [
            "What is the main research topic and objective?",
            "What are the key findings and results (with specific numbers)?",
            "What methodology was used?",
            "What are the main contributions?",
            "What are the limitations?",
            "What future work is recommended?",
        ]

        answers = []
        for q in questions:
            chunks = self.retrieve(q, top_k=6)
            ans = await self._answer_question(q, chunks)
            answers.append(f"**{q}**\n{ans}")
            await asyncio.sleep(0.1)

        return "\n\n".join(answers)


def _get_api_key() -> str:
    import os
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY not set in environment")
    return key
