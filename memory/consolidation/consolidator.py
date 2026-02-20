"""Memory consolidation orchestrator."""

from __future__ import annotations

from typing import Any

from memory.consolidation.contradiction_finder import ContradictionFinder
from memory.consolidation.forgetting import ForgettingPolicy
from memory.consolidation.pattern_miner import PatternMiner
from memory.consolidation.replay_engine import ReplayEngine


class Consolidator:
    """Runs full consolidation cycle for replay, contradictions, and retention."""

    def __init__(self, memory_manager: Any, llm_provider: Any | None = None) -> None:
        self.memory_manager = memory_manager
        self.replay_engine = ReplayEngine(memory_manager=memory_manager, llm_provider=llm_provider)
        self.contradiction_finder = ContradictionFinder(memory_manager=memory_manager)
        self.forgetting = ForgettingPolicy(memory_manager=memory_manager)
        self.pattern_miner = PatternMiner()

    def run(self) -> dict[str, Any]:
        replay_result = self.replay_engine.run()
        contradiction_result = self.contradiction_finder.run()
        forgetting_result = self.forgetting.run()
        patterns = self.pattern_miner.mine(self.memory_manager.list_episodes(limit=200))
        return {
            "replay": replay_result,
            "contradictions": contradiction_result,
            "forgetting": forgetting_result,
            "patterns": patterns,
        }
