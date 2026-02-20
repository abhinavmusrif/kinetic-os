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

    def run(self, mode: str = "light") -> dict[str, Any]:
        """Run consolidation cycle.
        
        Light mode: 
        - Propose minimal claims using heuristics.
        - Detect and resolve conflicts.
        
        Deep mode: 
        - Replay recent episodes (summarize semantics).
        - Extract procedures from successful sequences.
        - Run forgetting policy (pruning).
        - Mine patterns.
        """
        results: dict[str, Any] = {"mode": mode}
        recent_episodes = self.memory_manager.list_episodes(limit=50)
        
        if mode == "light":
            # 1. Propose semantic claims
            new_claims = self.memory_manager.propose_semantic_claims(recent_episodes, llm_optional=True)
            results["proposed_claims_count"] = len(new_claims)
            
            # 2. Detect and resolve conflicts
            conflicts = self.memory_manager.detect_conflicts(new_claims)
            if conflicts:
                self.memory_manager.resolve_conflicts(conflicts)
            results["conflicts_resolved"] = len(conflicts)
            
        elif mode == "deep":
            # 1. Replay via engine
            replay_result = self.replay_engine.run()
            results["replay"] = replay_result
            
            # 2. Extract procedures from successes
            successful_eps = [ep for ep in recent_episodes if ep.get("outcome") == "success"]
            procedures = self.memory_manager.extract_procedures_from_success(successful_eps, llm_optional=True)
            results["procedures_extracted"] = len(procedures)
            
            # 3. Contradiction finding (across all memory)
            contradiction_result = self.contradiction_finder.run()
            results["contradictions"] = contradiction_result
            
            # 4. Pattern Mining
            patterns = self.pattern_miner.mine(self.memory_manager.list_episodes(limit=200))
            results["patterns"] = patterns
            
            # 5. Forgetting / pruning old/unimportant episodes
            forgetting_result = self.forgetting.run()
            results["forgetting"] = forgetting_result
            
        return results
