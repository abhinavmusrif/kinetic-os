"""Memory retrieval tests."""

from __future__ import annotations

from pathlib import Path

from memory.memory_manager import MemoryManager
from memory.retrieval import MemoryRetriever
from memory.stores.sql_store import SQLStore


def build_memory(tmp_path: Path) -> MemoryManager:
    db_path = tmp_path / "ao.db"
    store = SQLStore(db_path=db_path)
    store.create_all()
    return MemoryManager(sql_store=store, context_limit=5)


def test_retrieval_returns_relevant_beliefs(tmp_path: Path) -> None:
    memory = build_memory(tmp_path)
    memory.upsert_semantic_claim(
        claim="User likely likes lo-fi music",
        confidence=0.9,
        support_episode_ids=[],
    )
    memory.upsert_semantic_claim(
        claim="User likely likes music videos",
        confidence=0.4,
        support_episode_ids=[],
    )

    retriever = MemoryRetriever(memory_manager=memory)
    hits = retriever.retrieve(query="music preference", k=3)
    assert hits["claims"]
    assert hits["claims"][0]["claim"] == "User likely likes lo-fi music"
    assert float(hits["claims"][0]["confidence"]) > float(hits["claims"][1]["confidence"])

def test_incremental_retrieval(tmp_path: Path) -> None:
    memory = build_memory(tmp_path)
    b1 = memory.upsert_semantic_claim(
        claim="First belief",
        confidence=0.9,
        support_episode_ids=[],
    )
    
    retriever = MemoryRetriever(memory_manager=memory)
    hits = retriever.retrieve(query="First", k=5)
    assert len(hits["claims"]) == 1
    
    # Store should have 1 item
    assert len(retriever.vector_store._items) == 1
    
    # Add another
    memory.upsert_semantic_claim(
        claim="Second belief",
        confidence=0.8,
        support_episode_ids=[],
    )
    
    hits2 = retriever.retrieve(query="Second", k=5)
    assert len(hits2["claims"]) == 2
