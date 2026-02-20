"""High-level memory manager over SQL and context buffer."""

from __future__ import annotations

import re
import uuid
from collections import deque
from datetime import UTC, datetime
from typing import Any

from memory.privacy import normalize_privacy_level
from memory.schemas import (
    BeliefRecord,
    EpisodeRecord,
    EvidenceRecord,
    GoalRecord,
    HypothesisRecord,
    SelfModelRecord,
    SkillRecord,
)
from memory.stores.sql_store import SQLStore
from memory.types.context import ContextMessage


class MemoryManager:
    """Manages all memory domains with SQLite persistence."""

    def __init__(self, sql_store: SQLStore, context_limit: int = 30) -> None:
        self.sql_store = sql_store
        self.sql_store.create_all()
        self.context_limit = context_limit
        self.context_buffer: deque[ContextMessage] = deque(maxlen=context_limit)
        self.retriever: Any | None = None

    def add_context_message(self, role: str, content: str) -> None:
        """Append a context message to session buffer."""
        self.context_buffer.append(ContextMessage(role=role, content=content))

    def get_context(self) -> list[dict[str, Any]]:
        """Return context messages as dictionaries."""
        return [msg.model_dump() for msg in self.context_buffer]

    def add_episode(
        self,
        summary: str,
        raw_context_refs: list[str],
        actions_taken: list[str],
        outcome: str,
        evidence_refs: list[str],
        confidence: float,
        tags: list[str],
        privacy_level: str,
    ) -> dict[str, Any]:
        """Insert episodic record."""
        record = EpisodeRecord(
            event_id=uuid.uuid4().hex,
            summary=summary,
            raw_context_refs=raw_context_refs,
            actions_taken=actions_taken,
            outcome=outcome,
            evidence_refs=evidence_refs,
            confidence=max(0.0, min(1.0, confidence)),
            tags=tags,
            privacy_level=normalize_privacy_level(privacy_level),
        )
        with self.sql_store.session() as sess:
            sess.add(record)
            sess.flush()
            payload = self._episode_to_dict(record)
        return payload

    def list_episodes(self, limit: int = 20) -> list[dict[str, Any]]:
        """List recent episodes."""
        with self.sql_store.session() as sess:
            rows = (
                sess.query(EpisodeRecord)
                .order_by(EpisodeRecord.timestamp.desc())
                .limit(limit)
                .all()
            )
            return [self._episode_to_dict(row) for row in rows]

    def add_belief(
        self,
        claim: str,
        confidence: float,
        status: str = "proposed",
        supporting_episode_ids: list[int] | None = None,
        conflicts_with_ids: list[int] | None = None,
        scope: str = "global",
    ) -> dict[str, Any]:
        """Insert semantic belief."""
        record = BeliefRecord(
            claim=claim,
            confidence=max(0.0, min(1.0, confidence)),
            status=status,
            supporting_episode_ids=supporting_episode_ids or [],
            conflicts_with_ids=conflicts_with_ids or [],
            scope=scope,
            last_confirmed_at=None,
        )
        with self.sql_store.session() as sess:
            sess.add(record)
            sess.flush()
            payload = self._belief_to_dict(record)
        return payload

    def update_belief(
        self,
        belief_id: int,
        *,
        status: str | None = None,
        confidence: float | None = None,
        conflicts_with_ids: list[int] | None = None,
        last_confirmed_at: datetime | None = None,
    ) -> dict[str, Any] | None:
        """Update belief fields by id."""
        with self.sql_store.session() as sess:
            row = sess.query(BeliefRecord).filter(BeliefRecord.id == belief_id).first()
            if not row:
                return None
            if status is not None:
                row.status = status
            if confidence is not None:
                row.confidence = max(0.0, min(1.0, confidence))
            if conflicts_with_ids is not None:
                row.conflicts_with_ids = conflicts_with_ids
            if last_confirmed_at is not None:
                row.last_confirmed_at = last_confirmed_at
            sess.flush()
            payload = self._belief_to_dict(row)
        return payload

    def list_beliefs(self, limit: int = 50, updated_after: datetime | None = None) -> list[dict[str, Any]]:
        """List semantic beliefs."""
        with self.sql_store.session() as sess:
            query = sess.query(BeliefRecord)
            if updated_after is not None:
                query = query.filter(BeliefRecord.updated_at > updated_after)
            rows = query.order_by(BeliefRecord.updated_at.desc()).limit(limit).all()
            return [self._belief_to_dict(row) for row in rows]

    def add_skill(
        self,
        name: str,
        trigger_conditions: str,
        steps: list[str],
        safety_constraints: list[str],
        success_criteria: str,
        known_failure_modes: list[str],
    ) -> dict[str, Any]:
        """Insert procedural skill."""
        record = SkillRecord(
            name=name,
            trigger_conditions=trigger_conditions,
            steps=steps,
            safety_constraints=safety_constraints,
            success_criteria=success_criteria,
            known_failure_modes=known_failure_modes,
        )
        with self.sql_store.session() as sess:
            sess.add(record)
            sess.flush()
            return self._skill_to_dict(record)

    def list_skills(self, limit: int = 20) -> list[dict[str, Any]]:
        """List procedural skills."""
        with self.sql_store.session() as sess:
            rows = sess.query(SkillRecord).limit(limit).all()
            return [self._skill_to_dict(row) for row in rows]

    def add_goal(
        self,
        goal_text: str,
        priority: int = 5,
        deadline: datetime | None = None,
        progress_state: str = "active",
        subgoals: list[str] | None = None,
        completion_criteria: str = "",
    ) -> dict[str, Any]:
        """Insert goal record."""
        record = GoalRecord(
            goal_text=goal_text,
            priority=priority,
            deadline=deadline,
            progress_state=progress_state,
            subgoals=subgoals or [],
            completion_criteria=completion_criteria,
        )
        with self.sql_store.session() as sess:
            sess.add(record)
            sess.flush()
            return self._goal_to_dict(record)

    def list_goals(self, limit: int = 20) -> list[dict[str, Any]]:
        """List goal records."""
        with self.sql_store.session() as sess:
            rows = sess.query(GoalRecord).order_by(GoalRecord.created_at.desc()).limit(limit).all()
            return [self._goal_to_dict(row) for row in rows]

    def upsert_self_model(
        self,
        tools_available: list[str],
        capabilities: str,
        limitations: str,
        reliability_scores: dict[str, float],
    ) -> dict[str, Any]:
        """Insert or update singleton self-model row."""
        with self.sql_store.session() as sess:
            row = sess.query(SelfModelRecord).order_by(SelfModelRecord.id.asc()).first()
            if row is None:
                row = SelfModelRecord(
                    tools_available=tools_available,
                    capabilities=capabilities,
                    limitations=limitations,
                    reliability_scores=reliability_scores,
                )
                sess.add(row)
            else:
                row.tools_available = tools_available
                row.capabilities = capabilities
                row.limitations = limitations
                row.reliability_scores = reliability_scores
                row.last_updated = datetime.now(UTC)
            sess.flush()
            return self._self_model_to_dict(row)

    def list_self_model(self) -> list[dict[str, Any]]:
        """List self-model rows."""
        with self.sql_store.session() as sess:
            rows = sess.query(SelfModelRecord).all()
            return [self._self_model_to_dict(row) for row in rows]

    def add_hypothesis(
        self,
        hypothesis: str,
        what_would_verify: str,
        evidence: list[str],
        risk_if_wrong: str,
        next_verification_action: str,
        confidence: float,
    ) -> dict[str, Any]:
        """Insert uncertainty hypothesis."""
        row = HypothesisRecord(
            hypothesis=hypothesis,
            what_would_verify=what_would_verify,
            evidence=evidence,
            risk_if_wrong=risk_if_wrong,
            next_verification_action=next_verification_action,
            confidence=max(0.0, min(1.0, confidence)),
        )
        with self.sql_store.session() as sess:
            sess.add(row)
            sess.flush()
            return self._hypothesis_to_dict(row)

    def list_hypotheses(self, limit: int = 20) -> list[dict[str, Any]]:
        """List uncertainty records."""
        with self.sql_store.session() as sess:
            rows = sess.query(HypothesisRecord).limit(limit).all()
            return [self._hypothesis_to_dict(row) for row in rows]

    def add_evidence(
        self,
        ref_id: str,
        source_type: str,
        source_path: str,
        content_hash: str,
    ) -> dict[str, Any]:
        """Insert evidence index row."""
        row = EvidenceRecord(
            ref_id=ref_id,
            source_type=source_type,
            source_path=source_path,
            content_hash=content_hash,
        )
        with self.sql_store.session() as sess:
            sess.add(row)
            sess.flush()
            return self._evidence_to_dict(row)

    def propose_belief_from_text(
        self,
        text: str,
        supporting_episode_ids: list[int],
    ) -> list[dict[str, Any]]:
        """Create belief proposals using simple preference extraction heuristics."""
        proposals: list[dict[str, Any]] = []
        patterns = [
            (r"\bi\s+love\s+([a-zA-Z0-9\-\s]+?)(?:\band\b|[.,;]|$)", "likes"),
            (r"\bi\s+like\s+([a-zA-Z0-9\-\s]+?)(?:\band\b|[.,;]|$)", "likes"),
            (r"\bi\s+prefer\s+([a-zA-Z0-9\-\s]+?)(?:\band\b|[.,;]|$)", "likes"),
            (r"\bi\s+dislike\s+([a-zA-Z0-9\-\s]+?)(?:\band\b|[.,;]|$)", "dislikes"),
            (r"\bi\s+hate\s+([a-zA-Z0-9\-\s]+?)(?:\band\b|[.,;]|$)", "dislikes"),
            (r"\bi\s+don't\s+like\s+([a-zA-Z0-9\-\s]+?)(?:\band\b|[.,;]|$)", "dislikes"),
            (r"\bi\s+do\s+not\s+like\s+([a-zA-Z0-9\-\s]+?)(?:\band\b|[.,;]|$)", "dislikes"),
        ]
        for pattern, sentiment in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if not match:
                continue
            topic = match.group(1).strip().rstrip(".")
            claim = f"User likely {sentiment} {topic}"
            proposals.append(
                self.add_belief(
                    claim=claim,
                    confidence=0.72 if sentiment == "likes" else 0.7,
                    status="proposed",
                    supporting_episode_ids=supporting_episode_ids,
                    scope="user_preferences",
                )
            )
        return proposals

    def inspect_recent(self, limit: int = 10) -> dict[str, list[dict[str, Any]]]:
        """Return compact memory inspection payload."""
        return {
            "episodes": self.list_episodes(limit=limit),
            "beliefs": self.list_beliefs(limit=limit),
            "goals": self.list_goals(limit=limit),
        }

    @staticmethod
    def _episode_to_dict(row: EpisodeRecord) -> dict[str, Any]:
        return {
            "id": row.id,
            "event_id": row.event_id,
            "timestamp": row.timestamp,
            "summary": row.summary,
            "raw_context_refs": list(row.raw_context_refs or []),
            "actions_taken": list(row.actions_taken or []),
            "outcome": row.outcome,
            "evidence_refs": list(row.evidence_refs or []),
            "confidence": row.confidence,
            "tags": list(row.tags or []),
            "privacy_level": row.privacy_level,
        }

    @staticmethod
    def _belief_to_dict(row: BeliefRecord) -> dict[str, Any]:
        return {
            "id": row.id,
            "claim": row.claim,
            "confidence": row.confidence,
            "status": row.status,
            "supporting_episode_ids": list(row.supporting_episode_ids or []),
            "conflicts_with_ids": list(row.conflicts_with_ids or []),
            "last_confirmed_at": row.last_confirmed_at,
            "scope": row.scope,
            "created_at": row.created_at,
            "updated_at": getattr(row, "updated_at", row.created_at),
        }

    @staticmethod
    def _skill_to_dict(row: SkillRecord) -> dict[str, Any]:
        return {
            "id": row.id,
            "name": row.name,
            "trigger_conditions": row.trigger_conditions,
            "steps": list(row.steps or []),
            "safety_constraints": list(row.safety_constraints or []),
            "success_criteria": row.success_criteria,
            "known_failure_modes": list(row.known_failure_modes or []),
        }

    @staticmethod
    def _goal_to_dict(row: GoalRecord) -> dict[str, Any]:
        return {
            "id": row.id,
            "goal_text": row.goal_text,
            "priority": row.priority,
            "created_at": row.created_at,
            "deadline": row.deadline,
            "progress_state": row.progress_state,
            "subgoals": list(row.subgoals or []),
            "completion_criteria": row.completion_criteria,
        }

    @staticmethod
    def _self_model_to_dict(row: SelfModelRecord) -> dict[str, Any]:
        return {
            "id": row.id,
            "tools_available": list(row.tools_available or []),
            "capabilities": row.capabilities,
            "limitations": row.limitations,
            "reliability_scores": dict(row.reliability_scores or {}),
            "last_updated": row.last_updated,
        }

    @staticmethod
    def _hypothesis_to_dict(row: HypothesisRecord) -> dict[str, Any]:
        return {
            "id": row.id,
            "hypothesis": row.hypothesis,
            "what_would_verify": row.what_would_verify,
            "evidence": list(row.evidence or []),
            "risk_if_wrong": row.risk_if_wrong,
            "next_verification_action": row.next_verification_action,
            "confidence": row.confidence,
        }

    @staticmethod
    def _evidence_to_dict(row: EvidenceRecord) -> dict[str, Any]:
        return {
            "id": row.id,
            "ref_id": row.ref_id,
            "source_type": row.source_type,
            "source_path": row.source_path,
            "content_hash": row.content_hash,
            "created_at": row.created_at,
        }
