"""Consolidation and contradiction tests."""

from __future__ import annotations

from pathlib import Path

from memory.consolidation.consolidator import Consolidator
from memory.consolidation.contradiction_finder import ContradictionFinder
from memory.memory_manager import MemoryManager
from memory.stores.sql_store import SQLStore
from llm.providers.mock_provider import MockProvider
from llm.base_llm import BaseLLM


def build_memory(tmp_path: Path) -> MemoryManager:
    db_path = tmp_path / "ao.db"
    store = SQLStore(db_path=db_path)
    store.create_all()
    return MemoryManager(sql_store=store, context_limit=5)


def test_consolidation_adds_belief_proposals_from_episodes(tmp_path: Path) -> None:
    memory = build_memory(tmp_path)
    memory.add_episode(
        summary="Remember I love lo-fi music",
        raw_context_refs=["test"],
        actions_taken=["parse"],
        outcome="captured",
        evidence_refs=[],
        confidence=0.9,
        tags=["chat"],
        privacy_level="internal",
    )
    consolidator = Consolidator(memory_manager=memory)
    result = consolidator.run()
    beliefs = memory.list_beliefs(limit=10)

    assert result["replay"]["candidate_beliefs"]
    assert any("lo-fi music" in belief["claim"].lower() for belief in beliefs)
    assert any(abs(float(belief["confidence"]) - 0.6) < 1e-9 for belief in beliefs)

class FakeLLMProvider(BaseLLM):
    def chat(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        return '[{"claim": "User explicitly stated preference for coding", "confidence": 0.95}]'

def test_consolidation_uses_llm_if_available(tmp_path: Path) -> None:
    memory = build_memory(tmp_path)
    memory.add_episode(
        summary="User discussed coding projects",
        raw_context_refs=[],
        actions_taken=[],
        outcome="",
        evidence_refs=[],
        confidence=0.9,
        tags=["chat"],
        privacy_level="internal",
    )
    fake_llm = FakeLLMProvider()
    consolidator = Consolidator(memory_manager=memory, llm_provider=fake_llm)
    result = consolidator.run()
    beliefs = memory.list_beliefs(limit=10)
    
    assert result["replay"]["candidate_beliefs"]
    assert any("coding" in belief["claim"].lower() for belief in beliefs)
    assert any(abs(float(belief["confidence"]) - 0.95) < 1e-9 for belief in beliefs)


def test_contradiction_detection_marks_disputed(tmp_path: Path) -> None:
    memory = build_memory(tmp_path)
    b1 = memory.add_belief(
        claim="User likely likes lo-fi music",
        confidence=0.7,
        status="proposed",
        scope="user_preferences",
    )
    b2 = memory.add_belief(
        claim="User likely dislikes lo-fi music",
        confidence=0.7,
        status="proposed",
        scope="user_preferences",
    )

    result = ContradictionFinder(memory_manager=memory).run()
    beliefs = {row["id"]: row for row in memory.list_beliefs(limit=20)}

    assert result["count"] >= 1
    assert beliefs[b1["id"]]["status"] == "disputed"
    assert beliefs[b2["id"]]["status"] == "disputed"
    assert b2["id"] in beliefs[b1["id"]]["conflicts_with_ids"]
    assert b1["id"] in beliefs[b2["id"]]["conflicts_with_ids"]
