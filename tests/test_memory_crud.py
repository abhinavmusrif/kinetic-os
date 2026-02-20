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
        summary="User asked for preference storage.",
        raw_context_refs=["test"],
        actions_taken=["mock_action"],
        outcome="stored",
        evidence_refs=["abc123"],
        confidence=0.8,
        tags=["test"],
        privacy_level="internal",
    )
    assert episode["id"] > 0

    belief = memory.add_belief(
        claim="User likely likes lo-fi music",
        confidence=0.72,
        status="proposed",
        supporting_episode_ids=[episode["id"]],
        scope="user_preferences",
    )
    assert belief["claim"].startswith("User likely likes")
    assert belief["status"] == "proposed"

    goal = memory.add_goal(
        goal_text="Remember music preference",
        progress_state="active",
        completion_criteria="Belief exists",
    )
    assert goal["goal_text"] == "Remember music preference"

    inspection = memory.inspect_recent(limit=5)
    assert len(inspection["episodes"]) >= 1
    assert len(inspection["beliefs"]) >= 1
    assert len(inspection["goals"]) >= 1
