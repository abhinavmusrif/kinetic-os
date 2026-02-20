"""Replay engine that mines episodes into memory updates."""

from __future__ import annotations

import json
import re
from typing import Any

from llm.providers.mock_provider import MockProvider


def _candidate_claims(text: str) -> list[tuple[str, float]]:
    patterns = [
        (r"\bi\s+love\s+([a-zA-Z0-9\-\s]+?)(?:\band\b|[.,;]|$)", "likes", 0.6),
        (r"\bi\s+like\s+([a-zA-Z0-9\-\s]+?)(?:\band\b|[.,;]|$)", "likes", 0.6),
        (r"\bi\s+prefer\s+([a-zA-Z0-9\-\s]+?)(?:\band\b|[.,;]|$)", "likes", 0.6),
        (r"\bi\s+dislike\s+([a-zA-Z0-9\-\s]+?)(?:\band\b|[.,;]|$)", "dislikes", 0.6),
        (r"\bi\s+hate\s+([a-zA-Z0-9\-\s]+?)(?:\band\b|[.,;]|$)", "dislikes", 0.6),
    ]
    candidates: list[tuple[str, float]] = []
    for pattern, sentiment, conf in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            topic = match.group(1).strip().rstrip(".")
            candidates.append((f"User likely {sentiment} {topic}", conf))
    return candidates


class ReplayEngine:
    """Reprocesses episodes into candidate beliefs and skill hints."""

    def __init__(self, memory_manager: Any, llm_provider: Any | None = None) -> None:
        self.memory_manager = memory_manager
        self.llm_provider = llm_provider

    def _extract_with_llm(self, text: str) -> list[tuple[str, float]]:
        if not self.llm_provider or isinstance(self.llm_provider, MockProvider):
            return _candidate_claims(text)
        prompt = (
            "Extract distinct user preferences, facts, or beliefs from the following text. "
            "Return ONLY a JSON array of objects with keys 'claim' (string) and 'confidence' (float 0.0-1.0). "
            f"Text: {text}"
        )
        try:
            response = self.llm_provider.chat([{"role": "user", "content": prompt}])
            match = re.search(r"\[.*\]", response, re.DOTALL)
            if not match:
                return _candidate_claims(text)
            parsed = json.loads(match.group())
            results = []
            for item in parsed:
                claim = item.get("claim")
                confidence = float(item.get("confidence", 0.7))
                if claim and isinstance(claim, str):
                    results.append((claim, confidence))
            if results:
                return results
            return _candidate_claims(text)
        except Exception:
            return _candidate_claims(text)

    def run(self, limit: int = 50) -> dict[str, Any]:
        """Generate candidate belief updates from recent episodes."""
        episodes = self.memory_manager.list_episodes(limit=limit)
        existing_beliefs = self.memory_manager.list_beliefs(limit=500)
        existing_by_claim: dict[str, list[dict[str, Any]]] = {}
        for belief in existing_beliefs:
            claim = str(belief["claim"])
            existing_by_claim.setdefault(claim, []).append(belief)
        added: list[dict[str, Any]] = []
        seen_claims: set[str] = set()

        for episode in episodes:
            episode_id = int(episode["id"])
            text_to_mine = episode["summary"] + " " + str(episode.get("outcome", ""))
            candidate_specs = self._extract_with_llm(text_to_mine)
            for claim, confidence in candidate_specs:
                existing_rows = existing_by_claim.get(claim, [])
                if existing_rows:
                    latest_updated: dict[str, Any] | None = None
                    for existing in existing_rows:
                        latest_updated = self.memory_manager.update_belief(
                            belief_id=int(existing["id"]),
                            status="proposed",
                            confidence=confidence,
                        )
                    if latest_updated is not None and claim not in seen_claims:
                        added.append(latest_updated)
                        seen_claims.add(claim)
                    continue
                created = self.memory_manager.add_belief(
                    claim=claim,
                    confidence=confidence,
                    status="proposed",
                    supporting_episode_ids=[episode_id],
                    scope="user_preferences",
                )
                existing_by_claim[claim] = [created]
                if claim not in seen_claims:
                    added.append(created)
                    seen_claims.add(claim)

        skill_update = {
            "name": "safe_goal_execution_pattern",
            "trigger_conditions": "goal contains user preference statement",
            "steps": [
                "decompose goal",
                "execute deterministic safe action",
                "store episodic and semantic memory",
            ],
            "safety_constraints": ["respect governance policies", "no risky tools by default"],
            "success_criteria": "belief proposal stored with provenance",
            "known_failure_modes": ["ambiguous preference phrasing", "conflicting evidence"],
        }
        return {
            "candidate_beliefs": added,
            "candidate_skill_update": skill_update,
            "verification_tasks": ["Ask user confirmation for newly proposed preference beliefs."],
        }
