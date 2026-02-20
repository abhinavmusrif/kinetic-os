"""Continuous Agentic Loop: Plan → Act → Observe → Evaluate → Adapt → Repeat.

The loop runs until the LLM evaluator determines the goal is complete,
or a max_iterations safety limit is reached.  After every action, the
loop captures the current screen state (via VLM or OCR fallback) so the
text LLM can reason about what actually happened.
"""

from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from core.event_bus import EventBus
from planner.task_decomposer import TaskDecomposer

logger = logging.getLogger("ao.control_loop")

# ── LLM prompts ──────────────────────────────────────────────────────

_EVALUATE_PROMPT = """\
You are the evaluation engine for an autonomous desktop operator.
After an action was taken, you must determine whether it succeeded by
looking at the new screen state.

Previous task: "{task}"
Action result: {action_outcome}
New screen state: {screen_state}

CRITICAL RULES:
- If an app fails to open or is not found, DO NOT hallucinate system-level
  recovery keys like Ctrl+Alt+Del, Alt+F4, or any panic shortcuts.
- Instead, suggest practical alternatives: adjust the app alias (e.g., try
  'msedge' instead of 'browser'), search the Start menu, or skip the step.
- Only mark goal_complete=true when the OVERALL GOAL is fully achieved.

Answer with ONLY a JSON object:
{{
  "succeeded": true/false,
  "reason": "<one-line explanation>",
  "goal_complete": true/false,
  "next_step": "<practical next action or empty string>"
}}
"""

_ADAPT_PROMPT = """\
You are the adaptation engine for an autonomous desktop operator.
The last action FAILED.  Based on the failure reason and screen state,
generate exactly ONE corrective action the agent should perform first.

Failed task: "{task}"
Failure reason: {reason}
Current screen state: {screen_state}

CRITICAL RULES:
- Do NOT suggest system-level panic keys (Ctrl+Alt+Del, Task Manager).
- Do NOT suggest restarting the computer or checking for updates.
- If an app failed to open, suggest trying a different alias or using the
  Start menu to search for it.
- If a click failed, suggest scrolling or re-focusing the correct window.
- Keep the corrective action simple and practical.

Reply with ONLY the corrective action as a single imperative sentence.
"""


@dataclass
class LoopResult:
    """Result of a full control-loop execution."""

    goal: str
    tasks_executed: list[str] = field(default_factory=list)
    action_results: list[dict[str, Any]] = field(default_factory=list)
    iterations: int = 0
    evaluation: str = ""
    adaptation: str = ""
    completed: bool = False


class ControlLoop:
    """Continuous agentic loop with screen-aware evaluation and adaptation."""

    def __init__(
        self,
        event_bus: EventBus,
        task_decomposer: TaskDecomposer,
        action_runner: Any,
        memory_manager: Any,
        llm: Any | None = None,
    ) -> None:
        self.event_bus = event_bus
        self.task_decomposer = task_decomposer
        self.action_runner = action_runner
        self.memory_manager = memory_manager
        self.llm = llm

    # ── Main entry point ─────────────────────────────────────────────

    def run_goal(self, goal: str, max_iterations: int = 15) -> LoopResult:
        """Execute a continuous agentic loop until the goal is complete.

        Plan → Act → Observe → Evaluate → Adapt → Repeat
        """
        self.event_bus.emit("plan_started", {"goal": goal})
        self.memory_manager.add_goal(
            goal_text=goal,
            priority=5,
            progress_json={"state": "in_progress"},
        )

        result = LoopResult(goal=goal)

        # ── PLAN: decompose the goal into initial task queue ──
        tasks = self.task_decomposer.decompose(goal)
        task_queue: deque[str] = deque(tasks)
        logger.info("Goal: %s — decomposed into %d tasks", goal, len(tasks))
        self.event_bus.emit("plan_completed", {"goal": goal, "tasks": list(task_queue)})

        self._log_plan(goal, tasks)

        iteration = 0
        while task_queue and iteration < max_iterations:
            iteration += 1
            current_task = task_queue.popleft()
            logger.info("Iteration %d/%d — executing: %s", iteration, max_iterations, current_task)

            # ── ACT ──
            self.event_bus.emit("act_started", {"task": current_task, "iteration": iteration})
            action_result = self.action_runner.run(task=current_task, goal=goal)
            result.tasks_executed.append(current_task)
            result.action_results.append(action_result)
            self.event_bus.emit("act_completed", {
                "task": current_task, "result": action_result, "iteration": iteration,
            })
            self._log_action(current_task, action_result, iteration)

            # ── OBSERVE: capture the new screen state ──
            screen_state = self._observe()
            self.event_bus.emit("observe", {
                "screen_state": screen_state[:200], "iteration": iteration,
            })

            # ── EVALUATE: ask the LLM if the action succeeded ──
            evaluation = self._evaluate(
                task=current_task,
                action_result=action_result,
                screen_state=screen_state,
                goal=goal,
            )
            self.event_bus.emit("evaluate", {"evaluation": evaluation, "iteration": iteration})
            self._log_evaluation(evaluation, iteration)

            # Check for goal completion
            if evaluation.get("goal_complete", False):
                result.completed = True
                result.evaluation = f"Goal '{goal}' completed at iteration {iteration}."
                result.adaptation = "None needed — goal achieved."
                logger.info("Goal COMPLETE at iteration %d", iteration)
                break

            # ── ADAPT: if the action failed, generate a corrective task ──
            if not evaluation.get("succeeded", True):
                corrective = self._adapt(
                    task=current_task,
                    reason=evaluation.get("reason", "Unknown failure"),
                    screen_state=screen_state,
                )
                if corrective:
                    logger.info("Adaptation: injecting corrective task: %s", corrective)
                    task_queue.appendleft(corrective)
                    result.adaptation = f"Injected corrective: {corrective}"
                    self._log_adaptation(corrective, iteration)

            # If the evaluator suggested a next step and the queue is empty
            next_step = evaluation.get("next_step", "")
            if next_step and not task_queue:
                task_queue.append(next_step)
                logger.info("Evaluator suggested next step: %s", next_step)

        # ── Finalize ──
        result.iterations = iteration
        if not result.completed:
            if iteration >= max_iterations:
                result.evaluation = f"Goal '{goal}' — max iterations ({max_iterations}) reached."
            else:
                result.evaluation = f"Goal '{goal}' — task queue exhausted after {iteration} iterations."
            result.adaptation = "Consider re-planning or providing more specific instructions."

        self.event_bus.emit("loop_completed", {
            "goal": goal,
            "iterations": iteration,
            "completed": result.completed,
            "timestamp": datetime.now(UTC).isoformat(),
        })

        self.memory_manager.add_episode(
            text=f"Goal loop finished: {result.evaluation}",
            structured_json={"goal": goal, "iterations": iteration, "completed": result.completed},
            source="control_loop",
            summary=result.evaluation,
            raw_context_refs=["control_loop", "final"],
            actions_taken=["loop_complete"],
            outcome="success" if result.completed else "incomplete",
            evidence_refs=[],
            confidence=0.9 if result.completed else 0.5,
            tags=["control-loop", "final"],
            privacy_level="internal",
        )

        return result

    # ── OBSERVE ──────────────────────────────────────────────────────

    def _observe(self) -> str:
        """Capture the current screen state.

        Priority:
        1. UI Automation tree (instant, primary)
        2. Screenshot + screen_reader (OCR/VLM fallback)
        """
        # ── Primary: UI Automation tree (instant) ──
        try:
            from os_controller.ui_tree_parser import (
                parse_active_window,
                build_tree_map,
            )

            elements = parse_active_window()
            if elements:
                tree_map = build_tree_map(elements)
                return f"Screen (UI tree, {len(elements)} elements):\n{tree_map}"
        except Exception as exc:
            logger.warning("UI tree observation failed: %s", exc)

        # ── Fallback: screenshot + screen_reader (OCR/VLM) ──
        try:
            os_tool = self.action_runner.tool_registry.get("os_automation_tool")
            if os_tool and hasattr(os_tool, "os_controller") and os_tool.os_controller:
                ctl = os_tool.os_controller
                capture = ctl.screen_capture.capture_screen()
                analysis = ctl.screen_reader.analyze(capture)
                spatial_map = analysis.get("spatial_map", "")
                state_summary = analysis.get("state_summary", "")
                return f"Screen (OCR fallback): {state_summary}\n{spatial_map}"
        except Exception as exc:
            logger.warning("Screen observation fallback failed: %s", exc)

        return "(Screen observation unavailable)"

    # ── EVALUATE ─────────────────────────────────────────────────────

    def _evaluate(
        self,
        task: str,
        action_result: dict[str, Any],
        screen_state: str,
        goal: str,
    ) -> dict[str, Any]:
        """Ask the LLM whether the action succeeded and if the goal is done."""
        if not self.llm:
            # Non-LLM fallback: simple success check
            succeeded = bool(action_result.get("success", False))
            return {
                "succeeded": succeeded,
                "reason": action_result.get("outcome", ""),
                "goal_complete": False,
                "next_step": "",
            }

        prompt = _EVALUATE_PROMPT.format(
            task=task,
            action_outcome=action_result.get("outcome", "unknown"),
            screen_state=screen_state[:1500],  # Cap context size
        )

        try:
            response = self.llm.chat([
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"Evaluate: did '{task}' succeed for goal '{goal}'?"},
            ])
            return self._parse_json_response(response, {
                "succeeded": bool(action_result.get("success", False)),
                "reason": action_result.get("outcome", ""),
                "goal_complete": False,
                "next_step": "",
            })
        except Exception as exc:
            logger.warning("LLM evaluation failed: %s", exc)
            return {
                "succeeded": bool(action_result.get("success", False)),
                "reason": str(exc),
                "goal_complete": False,
                "next_step": "",
            }

    # ── ADAPT ────────────────────────────────────────────────────────

    def _adapt(self, task: str, reason: str, screen_state: str) -> str:
        """Ask the LLM to generate a corrective task when an action fails."""
        if not self.llm:
            return ""

        prompt = _ADAPT_PROMPT.format(
            task=task,
            reason=reason,
            screen_state=screen_state[:1500],
        )

        try:
            response = self.llm.chat([
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"Generate corrective action for: {task}"},
            ])
            corrective = response.strip().strip('"').strip("'")
            return corrective if len(corrective) < 200 else corrective[:200]
        except Exception as exc:
            logger.warning("LLM adaptation failed: %s", exc)
            return ""

    # ── Helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _parse_json_response(response: str, defaults: dict[str, Any]) -> dict[str, Any]:
        """Parse a JSON response from the LLM, falling back to defaults."""
        import json
        import re

        try:
            cleaned = re.sub(r"```json\s*|```\s*", "", response).strip()
            match = re.search(r"\{[^}]+\}", cleaned, re.DOTALL)
            if match:
                data = json.loads(match.group())
                # Merge with defaults for any missing keys
                return {**defaults, **data}
        except (json.JSONDecodeError, ValueError):
            pass
        return defaults

    # ── Memory logging ───────────────────────────────────────────────

    def _log_plan(self, goal: str, tasks: list[str]) -> None:
        self.memory_manager.add_episode(
            text=f"Plan for goal: {goal}",
            structured_json={"goal": goal, "tasks": tasks},
            source="control_loop",
            summary=f"Decomposed into {len(tasks)} tasks",
            raw_context_refs=["control_loop", "plan"],
            actions_taken=["task_decomposition"],
            outcome="success",
            evidence_refs=[],
            confidence=0.85,
            tags=["control-loop", "plan"],
            privacy_level="internal",
        )

    def _log_action(self, task: str, result: dict[str, Any], iteration: int) -> None:
        self.memory_manager.add_episode(
            text=f"Executed: {task}",
            structured_json=result,
            source="executor",
            summary=f"Task: {task} (iter {iteration})",
            raw_context_refs=["control_loop"],
            actions_taken=[result.get("action", task)],
            outcome=str(result.get("success", False)),
            failure_reason=str(result.get("reason", "")),
            evidence_refs=result.get("evidence_refs", []),
            confidence=float(result.get("confidence", 0.7)),
            tags=["control-loop", "action"],
            privacy_level="internal",
        )

    def _log_evaluation(self, evaluation: dict[str, Any], iteration: int) -> None:
        self.memory_manager.add_episode(
            text=f"Evaluation iter {iteration}: {evaluation.get('reason', '')}",
            structured_json=evaluation,
            source="control_loop",
            summary=f"Eval iter {iteration}: succeeded={evaluation.get('succeeded')}",
            raw_context_refs=["control_loop", "evaluate"],
            actions_taken=["evaluate"],
            outcome="success" if evaluation.get("succeeded") else "failure",
            evidence_refs=[],
            confidence=0.82,
            tags=["control-loop", "evaluate"],
            privacy_level="internal",
        )

    def _log_adaptation(self, corrective: str, iteration: int) -> None:
        self.memory_manager.add_episode(
            text=f"Adaptation iter {iteration}: {corrective}",
            structured_json={"corrective_task": corrective, "iteration": iteration},
            source="control_loop",
            summary=f"Corrective task injected: {corrective}",
            raw_context_refs=["control_loop", "adapt"],
            actions_taken=["adapt"],
            outcome="corrective",
            evidence_refs=[],
            confidence=0.75,
            tags=["control-loop", "adapt"],
            privacy_level="internal",
        )

    # ── Chat interface (unchanged) ───────────────────────────────────

    def handle_chat_turn(self, user_text: str, llm: Any) -> str:
        """Handle one interactive chat turn."""
        response = llm.chat([
            {"role": "system", "content": "You are a safe autonomous operator."},
            {"role": "user", "content": user_text},
        ])
        self.memory_manager.add_context_message("user", user_text)
        self.memory_manager.add_context_message("assistant", response)
        self.memory_manager.add_episode(
            text=f"User: {user_text}\nAssistant: {response}",
            structured_json={"user_query": user_text, "response": response},
            source="chat",
            summary="Interactive chat turn",
            raw_context_refs=["chat"],
            actions_taken=["chat_response"],
            outcome="success",
            evidence_refs=[],
            confidence=0.8,
            tags=["chat"],
            privacy_level="internal",
        )
        return response
