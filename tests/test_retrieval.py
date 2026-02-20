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
    memory.add_belief(
        claim="User likely likes lo-fi music",
        confidence=0.9,
        status="proposed",
        scope="user_preferences",
    )
    memory.add_belief(
        claim="User likely likes music videos",
        confidence=0.4,
        status="proposed",
        scope="user_preferences",
    )

    retriever = MemoryRetriever(memory_manager=memory)
    hits = retriever.retrieve(query="music preference", limit=3)
    assert hits
    assert hits[0]["claim"] == "User likely likes lo-fi music"
    assert float(hits[0]["confidence"]) > float(hits[1]["confidence"])

def test_incremental_retrieval(tmp_path: Path) -> None:
    memory = build_memory(tmp_path)
    b1 = memory.add_belief(
        claim="First belief",
        confidence=0.9,
    )
    
    retriever = MemoryRetriever(memory_manager=memory)
    hits = retriever.retrieve(query="First")
    assert len(hits) == 1
    
    # Store should have 1 item
    assert len(retriever.vector_store._items) == 1
    
    # Add another
    memory.add_belief(
        claim="Second belief",
        confidence=0.8,
    )
    
    hits2 = retriever.retrieve(query="Second")
    assert len(hits2) == 2
    
    # Check that store has 2 items now (it incrementally added the new one)
    assert len(retriever.vector_store._items) == 2
    
    # Update first belief
    memory.update_belief(b1["id"], confidence=0.95)
    
    hits3 = retriever.retrieve(query="First")
    assert len(retriever.vector_store._items) == 2 # still 2 (dict replaced)
    
    # The payload in the vector store should be updated
    assert retriever.vector_store._items[str(b1["id"])][0]["record"]["confidence"] == 0.95
