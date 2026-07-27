from __future__ import annotations

import json
import logging
import math
import os
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class ProjectMemoryService:
    """
    Lightweight persistent project memory with hybrid lexical/vector-style retrieval.

    This avoids agents starting from zero by:
    - Bootstrapping architecture context from project docs
    - Indexing shared knowledge entries into a persistent local memory store
    - Supporting similarity search without requiring external vector DB dependencies
    """

    model_name = "procureflow-hybrid-memory-v1"

    def __init__(self) -> None:
        self.project_root = Path(__file__).resolve().parents[3]
        self.runtime_dir = self.project_root / "backend" / "runtime" / "memory"
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.runtime_dir / "project_memory_index.json"
        self.ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
        self.embedding_model = os.getenv("PROJECT_MEMORY_EMBED_MODEL", "nomic-embed-text:latest")
        self._index: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        if not self.index_path.exists():
            self._index = {}
            return
        try:
            self._index = json.loads(self.index_path.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning("Could not load project memory index: %s", exc)
            self._index = {}

    def _save(self) -> None:
        self.index_path.write_text(
            json.dumps(self._index, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )

    def _tokenize(self, text: str) -> Counter:
        tokens = re.findall(r"[a-z0-9_]{2,}", (text or "").lower())
        return Counter(tokens)

    def _vectorize(self, text: str) -> Dict[str, float]:
        counts = self._tokenize(text)
        if not counts:
            return {}
        norm = math.sqrt(sum(value * value for value in counts.values())) or 1.0
        return {token: value / norm for token, value in counts.items()}

    def _cosine_sparse(self, left: Dict[str, float], right: Dict[str, float]) -> float:
        if not left or not right:
            return 0.0
        if len(left) > len(right):
            left, right = right, left
        return sum(weight * right.get(token, 0.0) for token, weight in left.items())

    def _cosine_dense(self, left: List[float], right: List[float]) -> float:
        if not left or not right or len(left) != len(right):
            return 0.0
        dot = sum(a * b for a, b in zip(left, right))
        left_norm = math.sqrt(sum(a * a for a in left)) or 1.0
        right_norm = math.sqrt(sum(b * b for b in right)) or 1.0
        return dot / (left_norm * right_norm)

    async def get_embedding(self, text: str) -> Optional[List[float]]:
        clean_text = (text or "").strip()
        if not clean_text:
            return None
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.ollama_url}/api/embed",
                    json={"model": self.embedding_model, "input": clean_text[:8000]},
                )
            if response.status_code != 200:
                return None
            payload = response.json()
            embeddings = payload.get("embeddings", [])
            if not embeddings:
                return None
            vector = embeddings[0]
            if not isinstance(vector, list):
                return None
            return [float(value) for value in vector]
        except Exception:
            return None

    def upsert(
        self,
        entry_id: str,
        text: str,
        metadata: Dict[str, Any],
        dense_vector: Optional[List[float]] = None,
    ) -> None:
        clean_text = (text or "").strip()
        if not entry_id or not clean_text:
            return
        self._index[entry_id] = {
            "id": entry_id,
            "text": clean_text[:50000],
            "vector": self._vectorize(clean_text),
            "dense_vector": dense_vector or [],
            "metadata": metadata,
        }
        self._save()

    async def upsert_async(
        self,
        entry_id: str,
        text: str,
        metadata: Dict[str, Any],
        embed: bool = True,
    ) -> None:
        dense_vector = await self.get_embedding(text) if embed else None
        self.upsert(entry_id=entry_id, text=text, metadata=metadata, dense_vector=dense_vector)

    def _score_items(
        self,
        query: str,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        dense_query_vector: Optional[List[float]] = None,
    ) -> List[Dict[str, Any]]:
        if not query.strip():
            return []
        filters = filters or {}
        q_vector = self._vectorize(query)
        q_tokens = set(self._tokenize(query).keys())
        results: List[Dict[str, Any]] = []

        for item in self._index.values():
            metadata = item.get("metadata", {})
            if filters.get("entry_type") and metadata.get("entry_type") != filters["entry_type"]:
                continue
            if filters.get("tender_id") and metadata.get("tender_id") != filters["tender_id"]:
                continue
            if filters.get("agent_id") and metadata.get("agent_id") != filters["agent_id"]:
                continue

            text = item.get("text", "")
            text_tokens = set(item.get("vector", {}).keys())
            lexical_overlap = len(q_tokens & text_tokens)
            lexical_score = lexical_overlap / max(len(q_tokens), 1)
            sparse_score = self._cosine_sparse(q_vector, item.get("vector", {}))
            dense_score = 0.0
            dense_vector = item.get("dense_vector", [])
            if dense_query_vector and dense_vector:
                dense_score = self._cosine_dense(dense_query_vector, dense_vector)

            if dense_query_vector and dense_vector:
                score = round((dense_score * 0.6) + (sparse_score * 0.25) + (lexical_score * 0.15), 4)
            else:
                score = round((sparse_score * 0.75) + (lexical_score * 0.25), 4)

            if score <= 0:
                continue

            results.append(
                {
                    "entry_id": item["id"],
                    "score": score,
                    "summary": metadata.get("summary", "")[:500],
                    "text_preview": text[:400],
                    "metadata": metadata,
                }
            )

        results.sort(key=lambda row: row["score"], reverse=True)
        return results[:limit]

    def search(
        self,
        query: str,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        return self._score_items(query=query, limit=limit, filters=filters)

    async def search_async(
        self,
        query: str,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        dense_query_vector = await self.get_embedding(query)
        return self._score_items(
            query=query,
            limit=limit,
            filters=filters,
            dense_query_vector=dense_query_vector,
        )

    def _build_architecture_snapshot(self) -> str:
        backend_root = self.project_root / "backend" / "app"
        sections: List[str] = []

        if backend_root.exists():
            for folder_name in ["api", "agents", "services", "db"]:
                folder = backend_root / folder_name
                if not folder.exists():
                    continue
                py_files = sorted(folder.rglob("*.py"))
                file_count = len(py_files)
                route_count = 0
                class_count = 0
                function_count = 0
                for path in py_files[:200]:
                    try:
                        text = path.read_text(encoding="utf-8", errors="ignore")
                    except Exception:
                        continue
                    route_count += len(re.findall(r"@(?:router|app)\.(?:get|post|put|delete|patch)\(", text))
                    class_count += len(re.findall(r"^class\s+\w+", text, flags=re.MULTILINE))
                    function_count += len(re.findall(r"^(?:async\s+def|def)\s+\w+", text, flags=re.MULTILINE))
                sections.append(
                    f"{folder_name}: files={file_count}, routes={route_count}, classes={class_count}, functions={function_count}"
                )

        docs = [
            "Architecture snapshot generated from backend/app structure",
            *sections,
            "Important memory sources: AGENTS_ENTRY.md, AGENTS.md, CLAUDE.md, .memory/index.md, .memory/fixes-log.md",
        ]
        return "\n".join(docs)

    def bootstrap_project_context(self, force: bool = False) -> Dict[str, Any]:
        context_files = [
            self.project_root / "AGENTS_ENTRY.md",
            self.project_root / "AGENTS.md",
            self.project_root / "CLAUDE.md",
            self.project_root / ".memory" / "index.md",
            self.project_root / ".memory" / "fixes-log.md",
        ]
        added = 0
        for path in context_files:
            if not path.exists():
                continue
            entry_id = f"project-context::{path.name}"
            if not force and entry_id in self._index:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            self.upsert(
                entry_id=entry_id,
                text=text,
                metadata={
                    "entry_type": "project_context",
                    "agent_id": "system",
                    "tender_id": None,
                    "summary": f"Architecture context from {path.name}",
                    "source_file": str(path),
                    "tags": ["project-context", "architecture", "memory"],
                },
            )
            added += 1
        architecture_entry_id = "project-context::architecture-snapshot"
        if force or architecture_entry_id not in self._index:
            self.upsert(
                entry_id=architecture_entry_id,
                text=self._build_architecture_snapshot(),
                metadata={
                    "entry_type": "project_context",
                    "agent_id": "system",
                    "tender_id": None,
                    "summary": "Generated backend architecture snapshot",
                    "source_file": str(self.project_root / "backend" / "app"),
                    "tags": ["project-context", "architecture", "codebase"],
                },
            )
            added += 1
        return {"bootstrapped": added, "total_entries": len(self._index)}

    def get_context_entries(self, limit: int = 10) -> List[Dict[str, Any]]:
        entries = []
        for item in self._index.values():
            metadata = item.get("metadata", {})
            if metadata.get("entry_type") != "project_context":
                continue
            entries.append(
                {
                    "entry_id": item["id"],
                    "summary": metadata.get("summary", ""),
                    "source_file": metadata.get("source_file", ""),
                    "tags": metadata.get("tags", []),
                }
            )
        entries.sort(key=lambda row: row["entry_id"])
        return entries[:limit]

    def stats(self) -> Dict[str, Any]:
        project_context_entries = sum(
            1
            for item in self._index.values()
            if item.get("metadata", {}).get("entry_type") == "project_context"
        )
        return {
            "model": self.model_name,
            "embedding_model": self.embedding_model,
            "index_path": str(self.index_path),
            "total_entries": len(self._index),
            "project_context_entries": project_context_entries,
        }


project_memory_service = ProjectMemoryService()
