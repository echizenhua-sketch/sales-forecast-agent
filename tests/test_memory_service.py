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
