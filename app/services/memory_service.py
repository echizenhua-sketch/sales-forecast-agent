"""Long-term memory service for the assistant."""

from __future__ import annotations

import json
import math
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

from app.core.config import get_settings


class AssistantMemoryService:
    """
    Project-local assistant memory.

    The default backend is a JSONL fallback because the current model gateway does
    not expose an embeddings endpoint. The interface is intentionally small so a
    mem0 SDK backend can replace it when embeddings are available.
    """

    def __init__(self):
        settings = get_settings()
        self.enabled = bool(settings.memory_enabled)
        self.backend = (settings.memory_backend or "jsonl").lower()
        self.memory_dir = Path(settings.memory_dir)
        self.search_limit = int(settings.memory_search_limit or 5)
        self.memory_file = self.memory_dir / "memories.jsonl"
        self.embedding_api_base = (settings.embedding_api_base or "").rstrip("/")
        self.embedding_api_key = settings.embedding_api_key or ""
        self.embedding_model = settings.embedding_model or ""
        self.embedding_encoding_format = settings.embedding_encoding_format or "float"
        self.embedding_timeout = int(settings.embedding_timeout_seconds or 30)

        if self.enabled:
            self.memory_dir.mkdir(parents=True, exist_ok=True)

    def search(self, query: str, user_id: int | str | None, limit: int | None = None) -> list[dict[str, Any]]:
        """Search user-scoped long-term memories."""
        if not self.enabled or not query.strip():
            return []

        limit = limit or self.search_limit
        if self.backend == "vector_jsonl":
            return self._vector_search(query, user_id, limit)

        if self.backend != "jsonl":
            return []

        rows = self._load_rows()
        terms = self._tokenize(query)
        scored = []
        for row in rows:
            if str(row.get("user_id")) != str(user_id):
                continue
            memory = str(row.get("memory") or "")
            score = self._score(memory, terms)
            if score > 0:
                item = dict(row)
                item["score"] = score
                scored.append(item)

        scored.sort(key=lambda item: (item["score"], item.get("created_at", "")), reverse=True)
        return scored[:limit]

    def add_interaction(
        self,
        user_message: str,
        assistant_message: str,
        user_id: int | str | None,
        session_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Persist a compact memory candidate from a completed interaction."""
        if not self.enabled or self.backend not in {"jsonl", "vector_jsonl"}:
            return

        memory = self._build_memory_text(user_message, assistant_message)
        if not memory:
            return

        embedding = self._embed(memory) if self.backend == "vector_jsonl" else None
        if self.backend == "vector_jsonl" and not embedding:
            return

        row = {
            "created_at": datetime.now().isoformat(),
            "user_id": str(user_id),
            "session_id": session_id,
            "memory": memory,
            "metadata": metadata or {},
        }
        if embedding:
            row["embedding"] = embedding
        with self.memory_file.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    def format_for_prompt(self, memories: list[dict[str, Any]]) -> str:
        """Format memories as a compact prompt block."""
        lines = [str(item.get("memory") or "").strip() for item in memories]
        lines = [line for line in lines if line]
        if not lines:
            return ""
        return "\n".join(f"- {line}" for line in lines)

    def _load_rows(self) -> list[dict[str, Any]]:
        if not self.memory_file.exists():
            return []

        rows = []
        with self.memory_file.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return rows

    def _build_memory_text(self, user_message: str, assistant_message: str) -> str:
        text = user_message.strip()
        if not text:
            return ""

        if "记住" in text or "以后" in text or "关注" in text or "偏好" in text:
            return text[:500]

        # ponytail: heuristic fallback until embedding-backed mem0 extraction is available.
        if any(word in text for word in ("KA", "省大区", "缺口", "满足率", "排产", "SKU")):
            return f"用户问题：{text[:240]}；助手结论：{assistant_message.strip()[:240]}"
        return ""

    def _tokenize(self, text: str) -> set[str]:
        words = set(re.findall(r"[A-Za-z0-9_\-]+", text.lower()))
        for keyword in ("KA", "省大区", "缺口", "满足率", "排产", "SKU", "风险", "未满足"):
            if keyword.lower() in text.lower():
                words.add(keyword.lower())
        return words

    def _score(self, memory: str, terms: set[str]) -> int:
        lowered = memory.lower()
        return sum(1 for term in terms if term and term in lowered)

    def _vector_search(self, query: str, user_id: int | str | None, limit: int) -> list[dict[str, Any]]:
        query_embedding = self._embed(query)
        if not query_embedding:
            return []

        scored = []
        for row in self._load_rows():
            if str(row.get("user_id")) != str(user_id):
                continue
            embedding = row.get("embedding")
            if not isinstance(embedding, list):
                continue
            score = self._cosine_similarity(query_embedding, embedding)
            if score > 0:
                item = dict(row)
                item["score"] = score
                item.pop("embedding", None)
                scored.append(item)

        scored.sort(key=lambda item: (item["score"], item.get("created_at", "")), reverse=True)
        return scored[:limit]

    def _embed(self, text: str) -> list[float]:
        if not self.embedding_api_base or not self.embedding_api_key or not self.embedding_model:
            return []

        try:
            response = requests.post(
                f"{self.embedding_api_base}/embeddings",
                headers={
                    "Authorization": f"Bearer {self.embedding_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.embedding_model,
                    "input": text,
                    "encoding_format": self.embedding_encoding_format,
                },
                timeout=self.embedding_timeout,
            )
            response.raise_for_status()
            data = response.json()
            embedding = data.get("data", [{}])[0].get("embedding")
            if isinstance(embedding, list):
                return [float(value) for value in embedding]
        except Exception:
            return []
        return []

    def _cosine_similarity(self, left: list[float], right: list[float]) -> float:
        if not left or not right or len(left) != len(right):
            return 0.0

        dot = sum(a * b for a, b in zip(left, right))
        left_norm = math.sqrt(sum(a * a for a in left))
        right_norm = math.sqrt(sum(b * b for b in right))
        if not left_norm or not right_norm:
            return 0.0
        return dot / (left_norm * right_norm)
