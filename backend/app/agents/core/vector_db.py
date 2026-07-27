"""
Vector Knowledge Base — ChromaDB wrapper + RAG service.
Complements the existing ProjectMemoryService (hybrid lexical/vector JSON)
with a proper vector database for larger-scale semantic search.

Architecture:
  VectorDBService
    → ChromaDB collections (persistent storage)
    → EmbeddingService (Ollama primary, sentence-transformers fallback)
    → DocumentChunker (text splitting)

  RAGService
    → VectorDBService retrieval
    → LLMService generation
    → Structured output

Collections:
  - tender_documents: chunked tender document text
  - agent_knowledge: agent insights, patterns, rules
  - historical_outcomes: past bidding results for similarity search
"""

from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Generate dense embeddings using Ollama or local fallback."""

    def __init__(self, ollama_url: str = None, model: str = "nomic-embed-text"):
        self.ollama_url = (ollama_url or settings.OLLAMA_BASE_URL or "http://localhost:11434").rstrip("/")
        self.model = model
        self._local_model = None

    async def embed(self, texts: List[str]) -> List[List[float]]:
        """Embed texts. Returns list of embeddings (empty list for failures)."""
        if not texts:
            return []

        # Try Ollama first (batch embedding)
        try:
            import httpx
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{self.ollama_url}/api/embed",
                    json={"model": self.model, "input": texts},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    embeddings = data.get("embeddings", [])
                    if embeddings and len(embeddings) == len(texts):
                        return embeddings
        except Exception as e:
            logger.debug(f"Ollama embedding failed: {e}")

        # Fallback to local sentence-transformers
        return await self._embed_local(texts)

    async def _embed_local(self, texts: List[str]) -> List[List[float]]:
        try:
            if self._local_model is None:
                try:
                    from sentence_transformers import SentenceTransformer
                    self._local_model = SentenceTransformer('all-MiniLM-L6-v2')
                    logger.info("✓ Local embedding model loaded (all-MiniLM-L6-v2)")
                except ImportError:
                    logger.warning("sentence-transformers not installed — embeddings disabled")
                    return []
            if self._local_model:
                import numpy as np
                embeddings = self._local_model.encode(texts)
                return embeddings.tolist()
        except Exception as e:
            logger.warning(f"Local embedding failed: {e}")
        return []


class DocumentChunker:
    """Simple text chunking with overlap for documents."""

    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_text(self, text: str) -> List[str]:
        """Split text into overlapping chunks by word count."""
        if not text or not text.strip():
            return []
        words = text.split()
        if len(words) <= self.chunk_size:
            return [text.strip()]

        chunks = []
        start = 0
        while start < len(words):
            end = min(start + self.chunk_size, len(words))
            chunk = " ".join(words[start:end])
            chunks.append(chunk)
            start += self.chunk_size - self.chunk_overlap
            if start >= end:
                break
        return chunks

    def chunk_with_metadata(
        self, text: str, base_metadata: Dict = None
    ) -> List[Dict]:
        """Chunk text and return chunks with metadata."""
        chunks = self.chunk_text(text)
        return [
            {
                "text": chunk,
                "metadata": {**(base_metadata or {}), "chunk_index": i},
            }
            for i, chunk in enumerate(chunks)
        ]


class VectorDBService:
    """
    Vector database service using ChromaDB.
    Provides semantic search for tender documents and agent knowledge.

    If ChromaDB is not installed, the service gracefully degrades and
    logs warnings. Agents can still use ProjectMemoryService as fallback.
    """

    def __init__(self, persist_dir: str = None):
        self.persist_dir = persist_dir or str(
            Path(settings.BASE_DIR or ".") / "chroma_db"
        )
        self._client = None
        self._collections: Dict[str, Any] = {}
        self.embedding = EmbeddingService()
        self.chunker = DocumentChunker()
        self._available = None

    @property
    def is_available(self) -> bool:
        """Check if ChromaDB is available."""
        if self._available is None:
            self._available = self._check_available()
        return self._available

    def _check_available(self) -> bool:
        try:
            import chromadb
            return True
        except ImportError:
            logger.warning("chromadb not installed — vector search disabled")
            return False

    def _get_client(self):
        if self._client is None and self.is_available:
            try:
                import chromadb
                self._client = chromadb.PersistentClient(path=self.persist_dir)
                logger.info("✓ ChromaDB connected at %s", self.persist_dir)
            except Exception as e:
                logger.warning("Could not connect to ChromaDB: %s", e)
                self._client = False
        return self._client

    def _get_collection(self, name: str):
        """Get or create a collection."""
        if name in self._collections:
            return self._collections[name]
        client = self._get_client()
        if not client:
            return None
        try:
            collection = client.get_or_create_collection(
                name=name,
                metadata={"hnsw:space": "cosine"}
            )
            self._collections[name] = collection
            return collection
        except Exception as e:
            logger.warning(f"Could not create collection '{name}': {e}")
            return None

    # ------------------------------------------------------------------
    # Document operations
    # ------------------------------------------------------------------

    async def add_documents(
        self,
        collection: str,
        documents: List[str],
        metadatas: List[Dict] = None,
        ids: List[str] = None,
    ) -> int:
        """
        Add documents to a collection with automatic embedding generation.

        Returns:
            Number of documents successfully added
        """
        coll = self._get_collection(collection)
        if not coll:
            return 0

        if not documents:
            return 0

        if ids is None:
            ids = [str(uuid.uuid4()) for _ in documents]
        if metadatas is None:
            metadatas = [{} for _ in documents]

        # Generate embeddings
        embeddings = await self.embedding.embed(documents)

        # Filter out failed embeddings
        valid_docs, valid_meta, valid_ids, valid_emb = [], [], [], []
        for i, emb in enumerate(embeddings):
            if emb and len(emb) > 0:
                valid_docs.append(documents[i])
                valid_meta.append(metadatas[i])
                valid_ids.append(ids[i])
                valid_emb.append(emb)

        if not valid_docs:
            logger.warning("No valid embeddings generated for %s documents", len(documents))
            return 0

        try:
            coll.add(
                documents=valid_docs,
                metadatas=valid_meta,
                ids=valid_ids,
                embeddings=valid_emb,
            )
            logger.debug("Added %d documents to collection '%s'", len(valid_docs), collection)
            return len(valid_docs)
        except Exception as e:
            logger.warning(f"Could not add documents to ChromaDB: {e}")
            return 0

    async def query(
        self,
        collection: str,
        query_text: str,
        n_results: int = 5,
        where: Dict = None,
    ) -> List[Dict]:
        """
        Semantic search in a collection.

        Returns:
            List of results with keys: id, document, metadata, distance
        """
        coll = self._get_collection(collection)
        if not coll:
            return []

        try:
            embeddings = await self.embedding.embed([query_text])
            if not embeddings or not embeddings[0]:
                return []

            results = coll.query(
                query_embeddings=[embeddings[0]],
                n_results=n_results,
                where=where,
            )

            items = []
            for i in range(len(results["ids"][0])):
                items.append({
                    "id": results["ids"][0][i],
                    "document": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i] if results.get("metadatas") else {},
                    "distance": results["distances"][0][i] if results.get("distances") else 0,
                })
            return items
        except Exception as e:
            logger.warning(f"Vector query failed in '{collection}': {e}")
            return []

    async def delete(self, collection: str, ids: List[str]) -> bool:
        """Delete documents by ID."""
        coll = self._get_collection(collection)
        if not coll:
            return False
        try:
            coll.delete(ids=ids)
            return True
        except Exception as e:
            logger.warning(f"Could not delete from ChromaDB: {e}")
            return False

    async def get_collection_count(self, collection: str) -> int:
        """Get document count in a collection."""
        coll = self._get_collection(collection)
        if not coll:
            return 0
        try:
            return coll.count()
        except Exception:
            return 0

    # ------------------------------------------------------------------
    # Tender document ingestion
    # ------------------------------------------------------------------

    async def ingest_tender_document(
        self,
        tender_id: str,
        content: str,
        doc_type: str = "unknown",
        source_file: str = "",
    ) -> int:
        """Ingest a tender document: chunk, embed, and store."""
        chunks = self.chunker.chunk_text(content)
        if not chunks:
            return 0

        metadatas = []
        ids = []
        for i, chunk in enumerate(chunks):
            metadatas.append({
                "tender_id": tender_id,
                "doc_type": doc_type,
                "source_file": source_file,
                "chunk_index": i,
                "ingested_at": datetime_now_iso(),
            })
            ids.append(f"{tender_id}_{doc_type}_{i}")

        return await self.add_documents(
            collection="tender_documents",
            documents=chunks,
            metadatas=metadatas,
            ids=ids,
        )

    async def retrieve_for_tender(
        self,
        query: str,
        tender_id: str = None,
        n_results: int = 5,
    ) -> List[Dict]:
        """Retrieve relevant chunks for a tender query."""
        where = {"tender_id": tender_id} if tender_id else None
        return await self.query(
            collection="tender_documents",
            query_text=query,
            n_results=n_results,
            where=where,
        )

    # ------------------------------------------------------------------
    # Agent knowledge ingestion
    # ------------------------------------------------------------------

    async def ingest_agent_knowledge(
        self,
        agent_id: str,
        knowledge_items: List[Dict],
    ) -> int:
        """Ingest agent knowledge (insights, patterns, rules)."""
        documents = []
        metadatas = []
        ids = []

        for item in knowledge_items:
            documents.append(item.get("content", ""))
            metadatas.append({
                "agent_id": agent_id,
                "knowledge_type": item.get("type", "insight"),
                "tags": json.dumps(item.get("tags", [])),
                "confidence": item.get("confidence", 1.0),
                "created_at": datetime_now_iso(),
            })
            ids.append(f"{agent_id}_{item.get('id', str(uuid.uuid4()))}")

        return await self.add_documents(
            collection="agent_knowledge",
            documents=documents,
            metadatas=metadatas,
            ids=ids,
        )

    async def retrieve_for_agent(
        self,
        agent_id: str,
        query: str,
        n_results: int = 5,
    ) -> List[Dict]:
        """Retrieve agent-specific knowledge."""
        return await self.query(
            collection="agent_knowledge",
            query_text=query,
            n_results=n_results,
            where={"agent_id": agent_id},
        )

    # ------------------------------------------------------------------
    # Historical outcomes
    # ------------------------------------------------------------------

    async def ingest_historical_outcome(
        self,
        tender_id: str,
        outcome_text: str,
        metadata: Dict = None,
    ) -> int:
        """Ingest a historical bidding outcome for similarity search."""
        meta = {
            "tender_id": tender_id,
            "outcome_type": metadata.get("outcome_type", "unknown") if metadata else "unknown",
            "won": metadata.get("won", False) if metadata else False,
            "agency": metadata.get("agency", ""),
            "zone": metadata.get("zone", ""),
            "created_at": datetime_now_iso(),
        }
        return await self.add_documents(
            collection="historical_outcomes",
            documents=[outcome_text],
            metadatas=[meta],
            ids=[f"outcome_{tender_id}"],
        )

    async def retrieve_similar_outcomes(
        self,
        query: str,
        agency: str = None,
        n_results: int = 5,
    ) -> List[Dict]:
        """Find similar historical outcomes."""
        where = {"agency": agency} if agency else None
        return await self.query(
            collection="historical_outcomes",
            query_text=query,
            n_results=n_results,
            where=where,
        )

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    async def get_stats(self) -> Dict:
        """Get vector DB statistics."""
        if not self.is_available:
            return {"status": "disabled", "reason": "chromadb not installed"}

        try:
            client = self._get_client()
            if not client:
                return {"status": "error", "reason": "client not initialized"}

            collections = {
                "tender_documents": self._get_collection("tender_documents"),
                "agent_knowledge": self._get_collection("agent_knowledge"),
                "historical_outcomes": self._get_collection("historical_outcomes"),
            }

            stats = {}
            for name, coll in collections.items():
                if coll:
                    try:
                        stats[name] = coll.count()
                    except Exception:
                        stats[name] = 0
                else:
                    stats[name] = 0

            return {
                "status": "active",
                "persist_dir": self.persist_dir,
                "collections": stats,
                "embedding_model": self.embedding.model,
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}


class RAGService:
    """
    Retrieval-Augmented Generation service.
    Combines vector DB retrieval with LLM generation for intelligent answers.
    """

    def __init__(self, vector_db: VectorDBService, llm_service: Any = None):
        self.vector_db = vector_db
        self.llm_service = llm_service

    async def answer(
        self,
        query: str,
        collection: str = "tender_documents",
        n_results: int = 5,
        where: Dict = None,
        system_prompt: str = "",
    ) -> Dict:
        """
        RAG: retrieve relevant documents, then generate answer.

        Returns:
            Dict with keys: answer, sources, confidence, retrieved_count
        """
        # Retrieve
        results = await self.vector_db.query(
            collection=collection,
            query_text=query,
            n_results=n_results,
            where=where,
        )

        if not results:
            return {
                "answer": "No relevant information found in the knowledge base.",
                "sources": [],
                "confidence": 0.0,
                "retrieved_count": 0,
            }

        # Build context
        context_text = "\n\n---\n\n".join([
            f"[Source {i+1}]: {r['document']}"
            for i, r in enumerate(results)
        ])

        prompt = f"""Based on the following context, answer the question accurately.
If the context does not contain the answer, say so clearly.

CONTEXT:
{context_text}

QUESTION: {query}

Answer concisely using only the provided context."""

        # Generate
        if self.llm_service:
            try:
                response = await self.llm_service.generate(
                    prompt=prompt,
                    temperature=0.3,
                    system_prompt=system_prompt or (
                        "You are a procurement assistant. "
                        "Answer based ONLY on the provided context."
                    ),
                )
                answer = response.content
            except Exception as e:
                answer = f"LLM generation failed: {e}"
        else:
            answer = "LLM service not available for RAG generation."

        # Confidence: average distance (cosine similarity)
        distances = [r.get("distance", 0) for r in results if r.get("distance") is not None]
        avg_confidence = round(1.0 - (sum(distances) / len(distances)), 4) if distances else 0.0

        return {
            "answer": answer,
            "sources": results,
            "confidence": max(0.0, avg_confidence),
            "retrieved_count": len(results),
        }

    async def analyze_tender_with_rag(
        self,
        query: str,
        tender_id: str,
        llm_service: Any = None,
        n_results: int = 5,
    ) -> Dict:
        """Specialized RAG for tender document analysis."""
        llm = llm_service or self.llm_service
        return await self.answer(
            query=query,
            collection="tender_documents",
            n_results=n_results,
            where={"tender_id": tender_id},
            system_prompt=(
                "You are a tender document analyst for Bangladeshi civil works procurement. "
                "Answer based ONLY on the provided tender document excerpts."
            ),
        )


def datetime_now_iso() -> str:
    """ISO timestamp helper."""
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()
