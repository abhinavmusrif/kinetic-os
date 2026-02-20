"""Goal-to-task decomposition logic — LLM-first with regex fallback.

Includes CRITICAL CONSTRAINTS for Speed (desktop) and Stealth (web) to ensure
optimal behavior across native and browser contexts.
"""

from __future__ import annotations

import re
from typing import Any

_DECOMPOSITION_SYSTEM_PROMPT = """\
You are a task decomposition engine for an autonomous desktop operator.
Given a user's goal, break it down into a numbered list of atomic, sequential tasks.

CRITICAL CONSTRAINTS:
1. MAXIMIZE SPEED for desktop/OS tasks: heavily prioritize keyboard shortcuts \
and hotkeys (Win+R, Ctrl+S, Alt+F4, Ctrl+L, Enter, Tab). Avoid slow mouse \
movements when a hotkey exists. Use direct typing and clipboard paste.
2. MAXIMIZE STEALTH for web browser tasks: exclusively use human-like mouse \
movements and clicks. Never use rapid or instantaneous mouse teleportation \
on the web. Include natural pauses between browser interactions. Scroll in \
small human-like bursts. Type at human speed in web forms.

Rules:
- Each task must be a single, concrete action (e.g. "open notepad", "type hello world").
- Return ONLY the numbered list, one task per line.
- Do NOT include explanations, headers, or commentary.
- Keep each task short and imperative.
- Maximum 10 tasks.
- If the goal is already atomic, return it as a single task.
- For desktop tasks: prefer "press ctrl+s" over "click File > Save".
- For browser tasks: prefer "click the search bar" over "press ctrl+l".

Example input: "Open Chrome and search for Python tutorials"
Example output:
1. open chrome
2. wait for browser to load
3. click the address bar
4. type Python tutorials
5. press enter

Example input: "Save the current document"
Example output:
1. press ctrl+s
"""


class TaskDecomposer:
    """Decompose goals into safe executable tasks using LLM intelligence."""

    def __init__(self, llm: Any | None = None, retriever: Any | None = None) -> None:
        self.llm = llm
        self.retriever = retriever

    def decompose(self, goal: str) -> list[str]:
        """Split goal into task list — LLM first, regex fallback."""
        normalized = goal.strip()
        if not normalized:
            return ["Clarify empty goal with user."]

        # --- Primary: LLM-based decomposition ---
        if self.llm is not None:
            try:
                tasks = self._llm_decompose(normalized)
                if tasks:
                    return tasks
            except Exception:
                pass  # Fall through to regex fallback

        # --- Fallback: regex-based heuristic ---
        return self._regex_decompose(normalized)

    def _llm_decompose(self, goal: str) -> list[str]:
        """Use the LLM to decompose a goal into atomic tasks."""
        # Optionally enrich with retrieved memories
        memory_context = self._retrieve_context(goal)
        system_prompt = _DECOMPOSITION_SYSTEM_PROMPT
        if memory_context:
            system_prompt += f"\n\nRelevant context from memory:\n{memory_context}"

        response = self.llm.chat(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Decompose this goal: {goal}"},
            ]
        )

        return self._parse_llm_response(response)

    def _retrieve_context(self, goal: str) -> str:
        """Retrieve relevant memories to give the LLM planning context."""
        if not self.retriever:
            return ""
        try:
            memories = self.retriever.retrieve(
                query=goal, k=3, mode="hybrid", active_goal=goal
            )
            lines: list[str] = []
            for c in memories.get("claims", []):
                lines.append(f"- Belief: {c['claim']}")
            for p in memories.get("procedures", []):
                name = p.get("name", "Unknown")
                pattern = p.get("trigger_pattern", "")
                lines.append(f"- Known procedure '{name}': {pattern}")
            return "\n".join(lines)
        except Exception:
            return ""

    @staticmethod
    def _parse_llm_response(response: str) -> list[str]:
        """Parse numbered list from LLM response into clean task strings."""
        tasks: list[str] = []
        for line in response.splitlines():
            line = line.strip()
            if not line:
                continue
            # Strip numbering: "1. open notepad" → "open notepad"
            cleaned = re.sub(r"^\d+[\.)\]]\s*", "", line).strip()
            # Strip bullet markers: "- open notepad" → "open notepad"
            cleaned = re.sub(r"^[-*•]\s*", "", cleaned).strip()
            if cleaned:
                tasks.append(cleaned)
        return tasks[:10]  # Cap at 10 tasks

    @staticmethod
    def _regex_decompose(goal: str) -> list[str]:
        """Fallback: split on 'and', commas, semicolons."""
        parts = [
            p.strip()
            for p in re.split(r"\band\b|,|;", goal, flags=re.IGNORECASE)
            if p.strip()
        ]
        if parts:
            return parts
        return [goal]
