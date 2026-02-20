"""SQLAlchemy schemas for persistent memory tables."""

from __future__ import annotations

from datetime import UTC, datetime

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
    summary: Mapped[str] = mapped_column(Text)
    raw_context_refs: Mapped[list[str]] = mapped_column(JSON, default=list)
    actions_taken: Mapped[list[str]] = mapped_column(JSON, default=list)
    outcome: Mapped[str] = mapped_column(Text)
    evidence_refs: Mapped[list[str]] = mapped_column(JSON, default=list)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    privacy_level: Mapped[str] = mapped_column(String(32), default="internal")


class BeliefRecord(Base):
    """Semantic memory table."""

    __tablename__ = "beliefs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    claim: Mapped[str] = mapped_column(Text, index=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    status: Mapped[str] = mapped_column(String(32), default="proposed")
    supporting_episode_ids: Mapped[list[int]] = mapped_column(JSON, default=list)
    conflicts_with_ids: Mapped[list[int]] = mapped_column(JSON, default=list)
    last_confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    scope: Mapped[str] = mapped_column(String(64), default="global")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, index=True
    )


class SkillRecord(Base):
    """Procedural memory table."""

    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), unique=True)
    trigger_conditions: Mapped[str] = mapped_column(Text)
    steps: Mapped[list[str]] = mapped_column(JSON, default=list)
    safety_constraints: Mapped[list[str]] = mapped_column(JSON, default=list)
    success_criteria: Mapped[str] = mapped_column(Text)
    known_failure_modes: Mapped[list[str]] = mapped_column(JSON, default=list)


class GoalRecord(Base):
    """Goal memory table."""

    __tablename__ = "goals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    goal_text: Mapped[str] = mapped_column(Text, index=True)
    priority: Mapped[int] = mapped_column(Integer, default=5)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    progress_state: Mapped[str] = mapped_column(String(32), default="active")
    subgoals: Mapped[list[str]] = mapped_column(JSON, default=list)
    completion_criteria: Mapped[str] = mapped_column(Text, default="")


class SelfModelRecord(Base):
    """Self-model table."""

    __tablename__ = "self_model"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tools_available: Mapped[list[str]] = mapped_column(JSON, default=list)
    capabilities: Mapped[str] = mapped_column(Text, default="")
    limitations: Mapped[str] = mapped_column(Text, default="")
    reliability_scores: Mapped[dict[str, float]] = mapped_column(JSON, default=dict)
    last_updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


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
