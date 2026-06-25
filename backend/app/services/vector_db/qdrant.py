"""
Qdrant Vector Service — stores and retrieves reference embeddings
for semantic similarity search across the knowledge base.
"""
from __future__ import annotations

from typing import List, Dict, Any, Optional
import structlog
import asyncio

from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.exceptions import UnexpectedResponse
from sentence_transformers import SentenceTransformer

from app.core.config import settings

logger = structlog.get_logger()

VECTOR_DIM = 384  # all-MiniLM-L6-v2 output dimension


class VectorService:
    COLLECTION = settings.QDRANT_COLLECTION
    EMBED_MODEL = "all-MiniLM-L6-v2"

    def __init__(self):
        self._client: Optional[QdrantClient] = None
        self._embedder = SentenceTransformer(self.EMBED_MODEL)

    def _get_client(self) -> QdrantClient:
        if self._client is None:
            kwargs = {"url": settings.QDRANT_URL}
            if settings.QDRANT_API_KEY:
                kwargs["api_key"] = settings.QDRANT_API_KEY
            self._client = QdrantClient(**kwargs)
            self._ensure_collection()
        return self._client

    def _ensure_collection(self) -> None:
        client = self._client
        try:
            client.get_collection(self.COLLECTION)
        except Exception:
            client.create_collection(
                collection_name=self.COLLECTION,
                vectors_config=models.VectorParams(
                    size=VECTOR_DIM,
                    distance=models.Distance.COSINE,
                ),
                optimizers_config=models.OptimizersConfigDiff(
                    indexing_threshold=10000,
                ),
                hnsw_config=models.HnswConfigDiff(m=16, ef_construct=100),
            )
            logger.info("Qdrant collection created", collection=self.COLLECTION)

    def _embed(self, texts: List[str]) -> List[List[float]]:
        return self._embedder.encode(texts).tolist()

    async def store_references(self, references: List[Dict], project_id: str) -> None:
        if not references:
            return
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._store_sync, references, project_id)

    def _store_sync(self, references: List[Dict], project_id: str) -> None:
        try:
            client = self._get_client()
            texts = [
                f"{r.get('title', '')} {r.get('abstract', '')}"[:512]
                for r in references
            ]
            vectors = self._embed(texts)
            points = [
                models.PointStruct(
                    id=abs(hash(r.get("title", str(i)))) % (2**63),
                    vector=vec,
                    payload={
                        "project_id": project_id,
                        "title": r.get("title", ""),
                        "doi": r.get("doi", ""),
                        "authors": r.get("authors", [])[:3],
                        "year": r.get("year"),
                        "journal": r.get("journal", ""),
                        "citation_count": r.get("citation_count", 0),
                        "source": r.get("source", ""),
                    },
                )
                for i, (r, vec) in enumerate(zip(references, vectors))
            ]
            client.upsert(collection_name=self.COLLECTION, points=points)
            logger.debug("References stored in Qdrant", count=len(points))
        except Exception as e:
            logger.warning("Qdrant store failed", error=str(e))

    async def search_similar(self, query: str, limit: int = 10, score_threshold: float = 0.6) -> List[Dict]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._search_sync, query, limit, score_threshold)

    def _search_sync(self, query: str, limit: int, score_threshold: float) -> List[Dict]:
        try:
            client = self._get_client()
            vector = self._embed([query])[0]
            results = client.search(
                collection_name=self.COLLECTION,
                query_vector=vector,
                limit=limit,
                score_threshold=score_threshold,
                with_payload=True,
            )
            return [{"score": r.score, **r.payload} for r in results]
        except Exception as e:
            logger.warning("Qdrant search failed", error=str(e))
        return []

    async def find_related_papers(self, title: str, abstract: str, limit: int = 15) -> List[Dict]:
        query = f"{title} {abstract}"[:512]
        return await self.search_similar(query, limit=limit, score_threshold=0.5)
