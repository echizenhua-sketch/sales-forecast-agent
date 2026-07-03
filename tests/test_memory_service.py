"""Long-term assistant memory tests."""

import pytest

from app.core.config import get_settings
from app.services.memory_service import AssistantMemoryService


@pytest.fixture(autouse=True)
def clear_settings_cache():
    """Each test uses different environment-backed settings."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_disabled_memory_returns_empty_results(tmp_path, monkeypatch):
    """Disabled long-term memory should be a no-op."""
    monkeypatch.setenv("MEMORY_ENABLED", "false")
    monkeypatch.setenv("MEMORY_DIR", str(tmp_path / "memory"))

    service = AssistantMemoryService()

    assert service.search("KA部优先保障", user_id=1) == []
    service.add_interaction(
        user_message="我关注 KA 部",
        assistant_message="已记录",
        user_id=1,
        session_id="s1",
    )
    assert not (tmp_path / "memory" / "memories.jsonl").exists()


def test_jsonl_memory_search_and_add_interaction(tmp_path, monkeypatch):
    """Fallback JSONL memory should stay project-local and retrieve relevant facts."""
    memory_dir = tmp_path / "memory"
    monkeypatch.setenv("MEMORY_ENABLED", "true")
    monkeypatch.setenv("MEMORY_DIR", str(memory_dir))
    monkeypatch.setenv("MEMORY_BACKEND", "jsonl")

    service = AssistantMemoryService()
    service.add_interaction(
        user_message="请记住：我最关注 KA 部缺口和未满足金额",
        assistant_message="已记录你关注 KA 部缺口和未满足金额。",
        user_id=7,
        session_id="s1",
    )

    results = service.search("KA部缺口怎么处理", user_id=7, limit=3)

    assert results
    assert "KA 部缺口" in results[0]["memory"] or "KA部缺口" in results[0]["memory"]
    assert (memory_dir / "memories.jsonl").exists()


def test_jsonl_memory_is_scoped_by_user(tmp_path, monkeypatch):
    """One user's memories must not leak into another user's assistant context."""
    monkeypatch.setenv("MEMORY_ENABLED", "true")
    monkeypatch.setenv("MEMORY_DIR", str(tmp_path / "memory"))
    monkeypatch.setenv("MEMORY_BACKEND", "jsonl")

    service = AssistantMemoryService()
    service.add_interaction(
        user_message="请记住：我只看省大区风险",
        assistant_message="已记录。",
        user_id=1,
        session_id="s1",
    )

    assert service.search("省大区风险", user_id=2) == []


def test_vector_jsonl_uses_embedding_api_for_search(tmp_path, monkeypatch):
    """Vector JSONL memory should persist embeddings and rank by cosine similarity."""
    calls = []

    def fake_post(url, headers, json, timeout):
        calls.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
        text = json["input"]
        if "KA" in text:
            embedding = [1.0, 0.0, 0.0]
        else:
            embedding = [0.0, 1.0, 0.0]

        class FakeResponse:
            status_code = 200
            text = "{}"

            def json(self):
                return {
                    "object": "list",
                    "model": "Qwen/Qwen3-Embedding-8B",
                    "data": [{"embedding": embedding}],
                }

            def raise_for_status(self):
                return None

        return FakeResponse()

    monkeypatch.setenv("MEMORY_ENABLED", "true")
    monkeypatch.setenv("MEMORY_DIR", str(tmp_path / "memory"))
    monkeypatch.setenv("MEMORY_BACKEND", "vector_jsonl")
    monkeypatch.setenv("EMBEDDING_API_BASE", "https://embedding.local/v1")
    monkeypatch.setenv("EMBEDDING_API_KEY", "test-key")
    monkeypatch.setenv("EMBEDDING_MODEL", "Qwen/Qwen3-Embedding-8B")
    monkeypatch.setattr("app.services.memory_service.requests.post", fake_post)

    service = AssistantMemoryService()
    service.add_interaction(
        user_message="请记住：我最关注 KA 部缺口",
        assistant_message="已记录。",
        user_id=1,
        session_id="s1",
    )
    service.add_interaction(
        user_message="请记住：我关注省大区库存",
        assistant_message="已记录。",
        user_id=1,
        session_id="s2",
    )

    results = service.search("KA部缺口怎么处理", user_id=1, limit=1)

    assert results[0]["memory"] == "请记住：我最关注 KA 部缺口"
    assert results[0]["score"] > 0.99
    assert calls[0]["url"] == "https://embedding.local/v1/embeddings"
    assert calls[0]["json"]["model"] == "Qwen/Qwen3-Embedding-8B"
    assert calls[0]["json"]["encoding_format"] == "float"
    assert calls[0]["headers"]["Authorization"] == "Bearer test-key"
