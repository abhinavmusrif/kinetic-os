"""Contradiction detection for semantic beliefs."""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any


def _extract_sentiment_topic(claim: str) -> tuple[str, str] | None:
    patterns = [
        (r"user\s+likely\s+likes\s+(.+)", "likes"),
        (r"user\s+likely\s+dislikes\s+(.+)", "dislikes"),
    ]
    for pattern, sentiment in patterns:
        match = re.search(pattern, claim, flags=re.IGNORECASE)
        if match:
            topic = match.group(1).strip().lower().rstrip(".")
            return sentiment, topic
    return None


def _normalize_claim(claim: str) -> str:
    return re.sub(r"\s+", " ", claim.strip().lower().rstrip("."))


def _is_negation_conflict(claim_a: str, claim_b: str) -> bool:
    negation_tokens = (" not ", " never ", " no ")
    norm_a = _normalize_claim(claim_a)
    norm_b = _normalize_claim(claim_b)
    if norm_a == norm_b:
        return False

    # Direct inverse phrasing: one claim includes negation around shared phrase.
    a_has_neg = any(token in f" {norm_a} " for token in negation_tokens)
    b_has_neg = any(token in f" {norm_b} " for token in negation_tokens)
    if a_has_neg == b_has_neg:
        return False

    stripped_a = re.sub(r"\b(not|never|no)\b", "", norm_a).replace("  ", " ").strip()
    stripped_b = re.sub(r"\b(not|never|no)\b", "", norm_b).replace("  ", " ").strip()
    return bool(
        stripped_a and stripped_b and (stripped_a in stripped_b or stripped_b in stripped_a)
    )


class ContradictionFinder:
    """Find and mark conflicting beliefs."""

    def __init__(self, memory_manager: Any) -> None:
        self.memory_manager = memory_manager

    def run(self) -> dict[str, Any]:
        beliefs = self.memory_manager.list_beliefs(limit=500)
        by_id = {int(belief["id"]): belief for belief in beliefs}
        by_topic: dict[str, dict[str, list[int]]] = defaultdict(
            lambda: {"likes": [], "dislikes": []}
        )
        for belief in beliefs:
            parsed = _extract_sentiment_topic(belief["claim"])
            if parsed is None:
                continue
            sentiment, topic = parsed
            by_topic[topic][sentiment].append(int(belief["id"]))

        conflicts: list[dict[str, Any]] = []
        conflicting_pairs: set[tuple[int, int]] = set()

        for topic, bucket in by_topic.items():
            like_ids = bucket["likes"]
            dislike_ids = bucket["dislikes"]
            if not like_ids or not dislike_ids:
                continue
            conflict_ids = like_ids + dislike_ids
            for belief_id in conflict_ids:
                other_ids = [bid for bid in conflict_ids if bid != belief_id]
                self.memory_manager.update_belief(
                    belief_id=belief_id,
                    status="disputed",
                    conflicts_with_ids=other_ids,
                )
            for like_id in like_ids:
                for dislike_id in dislike_ids:
                    pair = (like_id, dislike_id) if like_id < dislike_id else (dislike_id, like_id)
                    conflicting_pairs.add(pair)
            conflicts.append({"topic": topic, "belief_ids": conflict_ids})

        belief_ids = sorted(by_id.keys())
        for i, belief_id_a in enumerate(belief_ids):
            for belief_id_b in belief_ids[i + 1 :]:
                claim_a = str(by_id[belief_id_a]["claim"])
                claim_b = str(by_id[belief_id_b]["claim"])
                if not _is_negation_conflict(claim_a, claim_b):
                    continue
                pair = (
                    (belief_id_a, belief_id_b)
                    if belief_id_a < belief_id_b
                    else (belief_id_b, belief_id_a)
                )
                if pair in conflicting_pairs:
                    continue
                conflicting_pairs.add(pair)

        for belief_id_a, belief_id_b in sorted(conflicting_pairs):
            updated_a = self.memory_manager.update_belief(
                belief_id=belief_id_a,
                status="disputed",
                conflicts_with_ids=sorted(
                    set(by_id[belief_id_a].get("conflicts_with_ids", [])) | {belief_id_b}
                ),
            )
            updated_b = self.memory_manager.update_belief(
                belief_id=belief_id_b,
                status="disputed",
                conflicts_with_ids=sorted(
                    set(by_id[belief_id_b].get("conflicts_with_ids", [])) | {belief_id_a}
                ),
            )
            if updated_a and updated_b:
                conflicts.append(
                    {
                        "topic": "negation_conflict",
                        "belief_ids": [belief_id_a, belief_id_b],
                    }
                )

        return {"conflicts_found": conflicts, "count": len(conflicts)}
