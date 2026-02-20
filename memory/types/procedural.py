"""Procedural memory models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ProceduralMemory(BaseModel):
    """Workflow memory for reusable skills."""

    name: str
    trigger_conditions: str
    steps: list[str] = Field(default_factory=list)
    safety_constraints: list[str] = Field(default_factory=list)
    success_criteria: str
    known_failure_modes: list[str] = Field(default_factory=list)
