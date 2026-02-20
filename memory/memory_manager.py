"""High-level memory manager over SQL and context buffer."""

from __future__ import annotations

import re
import uuid
from collections import deque
from datetime import UTC, datetime
from typing import Any

from memory.privacy import normalize_privacy_level
from memory.schemas import (
    EpisodeRecord,
    EvidenceRecord,
    GoalRecord,
    HypothesisRecord,
    SelfModelRecord,
    SemanticClaimRecord,
    ProcedureRecord,
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
        text: str,
        structured_json: dict[str, Any],
        source: str,
        evidence_refs: list[str],
        outcome: str,
        summary: str = "",
        raw_context_refs: list[str] | None = None,
        actions_taken: list[str] | None = None,
        failure_reason: str = "",
        confidence: float = 1.0,
        tags: list[str] | None = None,
        privacy_level: str = "internal",
        cost_tokens: int | None = None,
        cost_usd: float | None = None,
    ) -> dict[str, Any]:
        """Insert episodic record."""
        record = EpisodeRecord(
            event_id=uuid.uuid4().hex,
            source=source,
            text=text,
            structured_json=structured_json,
            summary=summary,
            raw_context_refs=raw_context_refs or [],
            actions_taken=actions_taken or [],
            outcome=outcome,
            failure_reason=failure_reason,
            evidence_refs=evidence_refs,
            confidence=max(0.0, min(1.0, confidence)),
            cost_tokens=cost_tokens,
            cost_usd=cost_usd,
            tags=tags or [],
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

    def upsert_semantic_claim(
        self,
        claim: str,
        support_episode_ids: list[str],
        confidence: float,
        claim_type: str = "belief",
        uncertainty_notes: str = "",
        scope: str = "global",
    ) -> dict[str, Any]:
        """Insert or update a semantic claim."""
        with self.sql_store.session() as sess:
            row = sess.query(SemanticClaimRecord).filter(SemanticClaimRecord.claim == claim).first()
            if not row:
                row = SemanticClaimRecord(
                    claim=claim,
                    type=claim_type,
                    confidence=max(0.0, min(1.0, confidence)),
                    uncertainty_notes=uncertainty_notes,
                    supporting_episode_ids=support_episode_ids,
                    scope=scope,
                )
                sess.add(row)
            else:
                row.confidence = max(0.0, min(1.0, confidence))
                # Merge supporting ids
                current_ids = set(row.supporting_episode_ids or [])
                current_ids.update(support_episode_ids)
                row.supporting_episode_ids = list(current_ids)
                if uncertainty_notes:
                    row.uncertainty_notes = uncertainty_notes
            sess.flush()
            payload = self._semantic_claim_to_dict(row)
        return payload

    def list_semantic_claims(self, limit: int = 50, updated_after: datetime | None = None) -> list[dict[str, Any]]:
        """List semantic claims."""
        with self.sql_store.session() as sess:
            query = sess.query(SemanticClaimRecord)
            if updated_after is not None:
                query = query.filter(SemanticClaimRecord.updated_at > updated_after)
            rows = query.order_by(SemanticClaimRecord.updated_at.desc()).limit(limit).all()
            return [self._semantic_claim_to_dict(row) for row in rows]

    def upsert_procedure(
        self,
        name: str,
        trigger_pattern: str,
        steps_json: list[dict[str, Any]],
        required_tools: list[str],
        verification_json: dict[str, Any],
        safety_constraints: list[str],
        success_rate: float = 1.0,
    ) -> dict[str, Any]:
        """Insert procedural skill."""
        with self.sql_store.session() as sess:
            row = sess.query(ProcedureRecord).filter(ProcedureRecord.name == name).first()
            if not row:
                row = ProcedureRecord(
                    name=name,
                    trigger_pattern=trigger_pattern,
                    steps_json=steps_json,
                    required_tools=required_tools,
                    verification_json=verification_json,
                    safety_constraints=safety_constraints,
                    success_rate=success_rate,
                )
                sess.add(row)
            else:
                row.trigger_pattern = trigger_pattern
                row.steps_json = steps_json
                row.required_tools = required_tools
                row.verification_json = verification_json
                row.safety_constraints = safety_constraints
                row.success_rate = success_rate
            sess.flush()
            return self._procedure_to_dict(row)

    def list_procedures(self, limit: int = 20) -> list[dict[str, Any]]:
        """List procedural skills."""
        with self.sql_store.session() as sess:
            rows = sess.query(ProcedureRecord).limit(limit).all()
            return [self._procedure_to_dict(row) for row in rows]

    def add_goal(
        self,
        goal_text: str,
        priority: int = 5,
        deadline: datetime | None = None,
        status: str = "active",
        parent_goal_id: int | None = None,
        progress_json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Insert goal record."""
        record = GoalRecord(
            goal_text=goal_text,
            priority=priority,
            deadline=deadline,
            status=status,
            parent_goal_id=parent_goal_id,
            progress_json=progress_json or {},
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
        capabilities_json: dict[str, Any],
        tool_reliability_json: dict[str, float],
        known_failure_modes_json: list[str],
        preferences_about_self_json: dict[str, Any],
    ) -> dict[str, Any]:
        """Insert or update singleton self-model row."""
        with self.sql_store.session() as sess:
            row = sess.query(SelfModelRecord).order_by(SelfModelRecord.id.asc()).first()
            if row is None:
                row = SelfModelRecord(
                    capabilities_json=capabilities_json,
                    tool_reliability_json=tool_reliability_json,
                    known_failure_modes_json=known_failure_modes_json,
                    preferences_about_self_json=preferences_about_self_json,
                )
                sess.add(row)
            else:
                row.capabilities_json = capabilities_json
                row.tool_reliability_json = tool_reliability_json
                row.known_failure_modes_json = known_failure_modes_json
                row.preferences_about_self_json = preferences_about_self_json
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

    def propose_semantic_claims(
        self,
        episodes_batch: list[dict[str, Any]],
        llm_optional: bool = True,
    ) -> list[dict[str, Any]]:
        """Create belief proposals. If no LLM, use simple preference extraction heuristics on text."""
        proposals: list[dict[str, Any]] = []
        patterns = [
            (r"\bi\s+love\s+([a-zA-Z0-9\-\s]+?)(?:\band\b|[.,;]|$)", "likes", 0.72),
            (r"\bi\s+like\s+([a-zA-Z0-9\-\s]+?)(?:\band\b|[.,;]|$)", "likes", 0.7),
            (r"\bi\s+prefer\s+([a-zA-Z0-9\-\s]+?)(?:\band\b|[.,;]|$)", "likes", 0.7),
            (r"\bi\s+dislike\s+([a-zA-Z0-9\-\s]+?)(?:\band\b|[.,;]|$)", "dislikes", 0.7),
            (r"\bi\s+hate\s+([a-zA-Z0-9\-\s]+?)(?:\band\b|[.,;]|$)", "dislikes", 0.72),
            (r"\bi\s+don't\s+like\s+([a-zA-Z0-9\-\s]+?)(?:\band\b|[.,;]|$)", "dislikes", 0.7),
            (r"\bi\s+do\s+not\s+like\s+([a-zA-Z0-9\-\s]+?)(?:\band\b|[.,;]|$)", "dislikes", 0.7),
        ]
        
        # Determine claims using heuristics for now.
        for ep in episodes_batch:
            text = ep.get("text", "") or ep.get("summary", "")
            for pattern, sentiment, base_conf in patterns:
                match = re.search(pattern, text, flags=re.IGNORECASE)
                if not match:
                    continue
                topic = match.group(1).strip().rstrip(".")
                claim = f"User likely {sentiment} {topic}"
                # Append to proposals
                proposals.append(
                    self.upsert_semantic_claim(
                        claim=claim,
                        confidence=base_conf,
                        support_episode_ids=[str(ep["id"])],
                        scope="user_preferences",
                    )
                )
        return proposals

    def detect_conflicts(self, new_claims: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Detect conflicts between new claims and existing semantic claims."""
        # Stub lexical check for now. In real impl, use semantic similarity / embeddings.
        conflicts = []
        existing = self.list_semantic_claims(limit=1000)
        # simplistic naive text overlap 
        for claim in new_claims:
            for ex in existing:
                if claim["id"] == ex["id"]:
                    continue
                # If they share topics but have opposing sentiments (e.g. likes X vs dislikes X)
                if "likes" in claim["claim"] and "dislikes" in ex["claim"]:
                    words_c = set(claim["claim"].split())
                    words_e = set(ex["claim"].split())
                    if len(words_c.intersection(words_e)) > 2:
                        conflicts.append({"new": claim, "existing": ex})
        return conflicts

    def resolve_conflicts(self, conflicts: list[dict[str, Any]], policy: str = "evidence_weighted") -> None:
        """Resolve detected conflicts by adjusting confidence levels."""
        with self.sql_store.session() as sess:
            for conflict in conflicts:
                new_c = conflict["new"]
                ext_c = conflict["existing"]
                
                new_row = sess.query(SemanticClaimRecord).filter(SemanticClaimRecord.id == new_c["id"]).first()
                ext_row = sess.query(SemanticClaimRecord).filter(SemanticClaimRecord.id == ext_c["id"]).first()
                if not new_row or not ext_row:
                    continue
                
                # Evidence weighted policy
                new_ev = len(new_row.supporting_episode_ids or [])
                ext_ev = len(ext_row.supporting_episode_ids or [])
                
                if new_ev > ext_ev:
                    ext_row.confidence *= 0.8
                    ext_row.contradiction_count += 1
                elif ext_ev > new_ev:
                    new_row.confidence *= 0.8
                    new_row.contradiction_count += 1
                else:
                    # Tie, decay both slightly
                    new_row.confidence *= 0.9
                    ext_row.confidence *= 0.9
                    new_row.contradiction_count += 1
                    ext_row.contradiction_count += 1
            sess.flush()

    def extract_procedures_from_success(self, episodes: list[dict[str, Any]], llm_optional: bool = True) -> list[dict[str, Any]]:
        """Extract repeatable skills from successful episodic sequences."""
        # Without an LLM, we cannot safely invent functional JSON steps.
        # Fallback to returning nothing safely. 
        proposals: list[dict[str, Any]] = []
        return proposals

    def update_self_model_from_runs(self, tool_outcomes: dict[str, dict[str, int]]) -> dict[str, Any] | None:
        """Update self-model reliability scores given a map of tool names to success/fail counts."""
        with self.sql_store.session() as sess:
            row = sess.query(SelfModelRecord).order_by(SelfModelRecord.id.asc()).first()
            if not row:
                return None
            
            # Make a copy to avoid mutating the dict directly if sqlalchemy proxies it
            rel_scores = dict(row.tool_reliability_json or {})
            
            for tool_name, outcomes in tool_outcomes.items():
                successes = outcomes.get("success", 0)
                fails = outcomes.get("fail", 0)
                total = successes + fails
                if total > 0:
                    current_rel = rel_scores.get(tool_name, 1.0)
                    new_rel = successes / total
                    # moving average
                    rel_scores[tool_name] = (current_rel * 0.7) + (new_rel * 0.3)
                    
            row.tool_reliability_json = rel_scores
            row.last_updated = datetime.now(UTC)
            sess.flush()
            return self._self_model_to_dict(row)

    def goal_update(self, goal_id: int, progress_json: dict[str, Any]) -> dict[str, Any] | None:
        """Update progress on a specific goal."""
        with self.sql_store.session() as sess:
            row = sess.query(GoalRecord).filter(GoalRecord.id == goal_id).first()
            if not row:
                return None
            row.progress_json = progress_json
            sess.flush()
            return self._goal_to_dict(row)

    def goal_close(self, goal_id: int, final_status: str) -> dict[str, Any] | None:
        """Mark a goal as done/failed etc."""
        with self.sql_store.session() as sess:
            row = sess.query(GoalRecord).filter(GoalRecord.id == goal_id).first()
            if not row:
                return None
            row.status = final_status
            sess.flush()
            return self._goal_to_dict(row)

    def inspect_recent(self, limit: int = 10) -> dict[str, list[dict[str, Any]]]:
        """Return compact memory inspection payload."""
        return {
            "episodes": self.list_episodes(limit=limit),
            "beliefs": self.list_semantic_claims(limit=limit),
            "goals": self.list_goals(limit=limit),
        }

    @staticmethod
    def _episode_to_dict(row: EpisodeRecord) -> dict[str, Any]:
        return {
            "id": row.id,
            "event_id": row.event_id,
            "timestamp": row.timestamp,
            "source": row.source,
            "summary": row.summary,
            "text": row.text,
            "structured_json": dict(row.structured_json or {}),
            "raw_context_refs": list(row.raw_context_refs or []),
            "actions_taken": list(row.actions_taken or []),
            "outcome": row.outcome,
            "failure_reason": row.failure_reason,
            "evidence_refs": list(row.evidence_refs or []),
            "confidence": row.confidence,
            "cost_tokens": row.cost_tokens,
            "cost_usd": row.cost_usd,
            "tags": list(row.tags or []),
            "privacy_level": row.privacy_level,
            "embedding": list(row.embedding or []) if row.embedding else None,
        }

    @staticmethod
    def _semantic_claim_to_dict(row: SemanticClaimRecord) -> dict[str, Any]:
        return {
            "id": row.id,
            "claim": row.claim,
            "type": row.type,
            "confidence": row.confidence,
            "uncertainty_notes": row.uncertainty_notes,
            "status": row.status,
            "supporting_episode_ids": list(row.supporting_episode_ids or []),
            "conflicts_with_ids": list(row.conflicts_with_ids or []),
            "contradiction_count": row.contradiction_count,
            "last_confirmed_at": row.last_confirmed_at,
            "scope": row.scope,
            "created_at": row.created_at,
            "updated_at": getattr(row, "updated_at", row.created_at),
        }

    @staticmethod
    def _procedure_to_dict(row: ProcedureRecord) -> dict[str, Any]:
        return {
            "id": row.id,
            "name": row.name,
            "trigger_pattern": row.trigger_pattern,
            "steps_json": list(row.steps_json or []),
            "required_tools": list(row.required_tools or []),
            "verification_json": dict(row.verification_json or {}),
            "safety_constraints": list(row.safety_constraints or []),
            "success_rate": row.success_rate,
            "last_run_ts": row.last_run_ts,
            "known_failure_modes": list(row.known_failure_modes or []),
        }

    @staticmethod
    def _goal_to_dict(row: GoalRecord) -> dict[str, Any]:
        return {
            "id": row.id,
            "goal_text": row.goal_text,
            "status": row.status,
            "parent_goal_id": row.parent_goal_id,
            "priority": row.priority,
            "created_at": row.created_at,
            "deadline": row.deadline,
            "progress_json": dict(row.progress_json or {}),
            "last_update_ts": getattr(row, "last_update_ts", row.created_at),
        }

    @staticmethod
    def _self_model_to_dict(row: SelfModelRecord) -> dict[str, Any]:
        return {
            "id": row.id,
            "capabilities_json": dict(row.capabilities_json or {}),
            "tool_reliability_json": dict(row.tool_reliability_json or {}),
            "known_failure_modes_json": list(row.known_failure_modes_json or []),
            "preferences_about_self_json": dict(row.preferences_about_self_json or {}),
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
