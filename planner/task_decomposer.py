"""Goal-to-task decomposition logic."""

from __future__ import annotations

import re
from typing import Any


class TaskDecomposer:
    """Decompose goals into safe executable tasks."""

    def __init__(self, llm: Any | None = None) -> None:
        self.llm = llm

    def decompose(self, goal: str) -> list[str]:
        """Split goal into task list using heuristic first, with optional LLM backup."""
        normalized = goal.strip()
        if not normalized:
            return ["Clarify empty goal with user."]

        # Heuristic: split on "and", commas, semicolons.
        parts = [
            p.strip()
            for p in re.split(r"\band\b|,|;", normalized, flags=re.IGNORECASE)
            if p.strip()
        ]
        tasks = [f"Task: {part}" for part in parts]
        if len(tasks) > 0:
            return tasks

        if self.llm is not None:
            response = self.llm.chat(
                [
                    {"role": "system", "content": "Decompose into concise steps."},
                    {"role": "user", "content": f"Decompose: {goal}"},
                ]
            )
            lines = [line.strip("- ").strip() for line in response.splitlines() if line.strip()]
            if lines:
                return lines[:5]
        return [f"Task: {normalized}"]
