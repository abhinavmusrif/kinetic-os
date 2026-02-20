"""SQLAlchemy schemas for persistent memory tables."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utc_now() -> datetime:
    """Return UTC datetime for default timestamps."""
    return datetime.now(UTC)


class Base(DeclarativeBase):
    """Declarative base."""


class EpisodeRecord(Base):
    """Episodic memory table."""

    __tablename__ = "episodes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    source: Mapped[str] = mapped_column(String(32), default="system")
    summary: Mapped[str] = mapped_column(Text)
    text: Mapped[str] = mapped_column(Text, default="")
    structured_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    raw_context_refs: Mapped[list[str]] = mapped_column(JSON, default=list)
    actions_taken: Mapped[list[str]] = mapped_column(JSON, default=list)
    outcome: Mapped[str] = mapped_column(Text, default="unknown")
    failure_reason: Mapped[str] = mapped_column(Text, default="")
    evidence_refs: Mapped[list[str]] = mapped_column(JSON, default=list)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    cost_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    privacy_level: Mapped[str] = mapped_column(String(32), default="internal")
    embedding: Mapped[list[float] | None] = mapped_column(JSON, nullable=True)


class SemanticClaimRecord(Base):
    """Semantic memory table."""

    __tablename__ = "semantic_claims"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    claim: Mapped[str] = mapped_column(Text, index=True)
    type: Mapped[str] = mapped_column(String(32), default="belief")  # preference/belief/fact/rule
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    uncertainty_notes: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), default="proposed")
    supporting_episode_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    conflicts_with_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    contradiction_count: Mapped[int] = mapped_column(Integer, default=0)
    last_confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    scope: Mapped[str] = mapped_column(String(64), default="global")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, index=True
    )


class ProcedureRecord(Base):
    """Procedural memory table (Skill memory)."""

    __tablename__ = "procedures"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), unique=True)
    trigger_pattern: Mapped[str] = mapped_column(Text)
    steps_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    required_tools: Mapped[list[str]] = mapped_column(JSON, default=list)
    verification_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    safety_constraints: Mapped[list[str]] = mapped_column(JSON, default=list)
    success_rate: Mapped[float] = mapped_column(Float, default=1.0)
    last_run_ts: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    known_failure_modes: Mapped[list[str]] = mapped_column(JSON, default=list)


class GoalRecord(Base):
    """Goal memory table."""

    __tablename__ = "goals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    goal_text: Mapped[str] = mapped_column(Text, index=True)
    status: Mapped[str] = mapped_column(String(32), default="active")
    parent_goal_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    priority: Mapped[int] = mapped_column(Integer, default=5)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    progress_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    last_update_ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class SelfModelRecord(Base):
    """Self-model table."""

    __tablename__ = "self_model"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    capabilities_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    tool_reliability_json: Mapped[dict[str, float]] = mapped_column(JSON, default=dict)
    known_failure_modes_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    preferences_about_self_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    last_updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class MemoryEventRecord(Base):
    """Memory events log table."""

    __tablename__ = "memory_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class HypothesisRecord(Base):
    """Uncertainty ledger table."""

    __tablename__ = "hypotheses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    hypothesis: Mapped[str] = mapped_column(Text)
    what_would_verify: Mapped[str] = mapped_column(Text)
    evidence: Mapped[list[str]] = mapped_column(JSON, default=list)
    risk_if_wrong: Mapped[str] = mapped_column(Text, default="unknown")
    next_verification_action: Mapped[str] = mapped_column(Text, default="")
    confidence: Mapped[float] = mapped_column(Float, default=0.5)


class EvidenceRecord(Base):
    """Evidence index table."""

    __tablename__ = "evidence"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ref_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    source_type: Mapped[str] = mapped_column(String(32))
    source_path: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(128), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
