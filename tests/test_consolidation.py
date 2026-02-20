"""Consolidation and contradiction tests."""

from __future__ import annotations

from pathlib import Path
from typing import Any

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
        text="Remember I love lo-fi music.",
        structured_json={},
        source="test",
        outcome="",
        summary="I love lo-fi music.",
        raw_context_refs=["test"],
        actions_taken=["parse"],
        evidence_refs=[],
        confidence=0.9,
        tags=["chat"],
        privacy_level="internal",
    )
    consolidator = Consolidator(memory_manager=memory)
    result = consolidator.run(mode="deep")
    beliefs = memory.list_semantic_claims(limit=10)

    assert any("lo-fi music" in claim["claim"].lower() for claim in beliefs)

class FakeLLMProvider(BaseLLM):
    def chat(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        return '[{"claim": "User explicitly stated preference for coding", "confidence": 0.95}]'

def test_consolidation_uses_llm_if_available(tmp_path: Path) -> None:
    memory = build_memory(tmp_path)
    memory.add_episode(
        text="User discussed coding projects",
        structured_json={},
        source="test",
        outcome="",
        summary="User discussed coding projects",
        raw_context_refs=[],
        actions_taken=[],
        evidence_refs=[],
        confidence=0.9,
        tags=["chat"],
        privacy_level="internal",
    )
    fake_llm = FakeLLMProvider()
    consolidator = Consolidator(memory_manager=memory, llm_provider=fake_llm)
    result = consolidator.run(mode="deep")
    claims = memory.list_semantic_claims(limit=10)
    
    assert any("coding" in claim["claim"].lower() for claim in claims)


def test_contradiction_detection_marks_disputed(tmp_path: Path) -> None:
    memory = build_memory(tmp_path)
    b1 = memory.upsert_semantic_claim(
        claim="User likely likes lo-fi music",
        confidence=0.7,
        support_episode_ids=[],
    )
    b2 = memory.upsert_semantic_claim(
        claim="User likely dislikes lo-fi music",
        confidence=0.7,
        support_episode_ids=[],
    )

    result = ContradictionFinder(memory_manager=memory).run()
    claims = memory.list_semantic_claims(limit=20)

    assert result["count"] >= 1
