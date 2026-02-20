"""Memory CRUD tests."""

from __future__ import annotations

from pathlib import Path

from memory.memory_manager import MemoryManager
from memory.stores.sql_store import SQLStore


def build_memory(tmp_path: Path) -> MemoryManager:
    db_path = tmp_path / "ao.db"
    store = SQLStore(db_path=db_path)
    store.create_all()
    return MemoryManager(sql_store=store, context_limit=5)


def test_memory_db_create_and_crud(tmp_path: Path) -> None:
    memory = build_memory(tmp_path)

    episode = memory.add_episode(
        text="User asked for preference storage.",
        structured_json={},
        source="test",
        outcome="stored",
        summary="User asked for preference storage.",
        raw_context_refs=["test"],
        actions_taken=["mock_action"],
        evidence_refs=["abc123"],
        confidence=0.8,
        tags=["test"],
        privacy_level="internal",
    )
    assert episode["id"] > 0

    claim = memory.upsert_semantic_claim(
        claim="User likely likes lo-fi music",
        confidence=0.72,
        support_episode_ids=[str(episode["id"])],
    )
    assert claim["claim"].startswith("User likely likes")

    goal = memory.add_goal(
        goal_text="Remember music preference",
        progress_json={"state": "active"},
    )
    assert goal["goal_text"] == "Remember music preference"

    inspection = memory.inspect_recent(limit=5)
    assert len(inspection["episodes"]) >= 1
    assert len(inspection["beliefs"]) >= 1
    assert len(inspection["goals"]) >= 1
