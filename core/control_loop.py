"""Core Plan -> Act -> Observe -> Evaluate -> Adapt loop."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from core.event_bus import EventBus
from planner.task_decomposer import TaskDecomposer


@dataclass
class LoopResult:
    """Result of one control-loop execution."""

    goal: str
    tasks: list[str]
    action_results: list[dict[str, Any]]
    evaluation: str
    adaptation: str


class ControlLoop:
    """Drives goal execution with event emission and memory logging hooks."""

    def __init__(
        self,
        event_bus: EventBus,
        task_decomposer: TaskDecomposer,
        action_runner: Any,
        memory_manager: Any,
    ) -> None:
        self.event_bus = event_bus
        self.task_decomposer = task_decomposer
        self.action_runner = action_runner
        self.memory_manager = memory_manager

    def run_goal(self, goal: str, max_steps: int = 5) -> LoopResult:
        """Execute a bounded autonomous control loop for a goal."""
        self.event_bus.emit("plan_started", {"goal": goal})
        self.memory_manager.add_goal(
            goal_text=goal,
            priority=5,
            progress_state="in_progress",
            completion_criteria=f"Run up to {max_steps} execution cycles and log memory artifacts.",
        )
        
        all_action_results: list[dict[str, Any]] = []
        all_tasks: list[str] = []
        final_eval = "Goal not evaluated."
        final_adapt = "None"
        
        for step_idx in range(1, max_steps + 1):
            tasks = self.task_decomposer.decompose(goal)
            all_tasks.extend(tasks)
            self.event_bus.emit("plan_completed", {"goal": goal, "tasks": tasks, "step": step_idx})
            self.memory_manager.add_episode(
                summary=f"Plan generated for goal: {goal} (Step {step_idx})",
                raw_context_refs=["control_loop", "plan"],
                actions_taken=["task_decomposition"],
                outcome=f"Generated {len(tasks)} tasks",
                evidence_refs=[],
                confidence=0.85,
                tags=["control-loop", "plan"],
                privacy_level="internal",
            )

            action_results: list[dict[str, Any]] = []
            for task in tasks:
                self.event_bus.emit("act_started", {"task": task, "step": step_idx})
                result = self.action_runner.run(task=task, goal=goal)
                action_results.append(result)
                all_action_results.append(result)
                self.event_bus.emit("act_completed", {"task": task, "result": result, "step": step_idx})
                
                self.memory_manager.add_episode(
                    summary=f"Executed task: {task} (Step {step_idx})",
                    raw_context_refs=["control_loop"],
                    actions_taken=[result.get("action", "unknown")],
                    outcome=result.get("outcome", "unknown"),
                    evidence_refs=result.get("evidence_refs", []),
                    confidence=float(result.get("confidence", 0.7)),
                    tags=["control-loop", "goal-run"],
                    privacy_level="internal",
                )

            observation = f"Completed {len(action_results)} actions in step {step_idx}."
            self.event_bus.emit("observe", {"observation": observation, "step": step_idx})
            self.memory_manager.add_episode(
                summary=f"Observation step {step_idx} completed",
                raw_context_refs=["control_loop", "observe"],
                actions_taken=["observe"],
                outcome=observation,
                evidence_refs=[],
                confidence=0.8,
                tags=["control-loop", "observe"],
                privacy_level="internal",
            )

            final_eval = self._evaluate(goal=goal, action_results=action_results)
            final_adapt = self._adapt(goal=goal, evaluation=final_eval)
            self.memory_manager.add_episode(
                summary=f"Evaluation and adaptation step {step_idx} completed",
                raw_context_refs=["control_loop", "evaluate", "adapt"],
                actions_taken=["evaluate", "adapt"],
                outcome=f"{final_eval} {final_adapt}",
                evidence_refs=[],
                confidence=0.82,
                tags=["control-loop", "evaluate", "adapt"],
                privacy_level="internal",
            )

            if "successfully" in final_eval.lower():
                break
                
            if all(not r.get("success") for r in action_results):
                final_eval += " (Aborted early due to zero successes in step)"
                break

        self.event_bus.emit(
            "loop_completed",
            {
                "goal": goal,
                "tasks": all_tasks,
                "evaluation": final_eval,
                "adaptation": final_adapt,
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )
        return LoopResult(
            goal=goal,
            tasks=all_tasks,
            action_results=all_action_results,
            evaluation=final_eval,
            adaptation=final_adapt,
        )

    def handle_chat_turn(self, user_text: str, llm: Any) -> str:
        """Handle one chat turn and log as episodic memory."""
        response = llm.chat(
            [
                {"role": "system", "content": "You are a safe autonomous operator."},
                {"role": "user", "content": user_text},
            ]
        )
        self.memory_manager.add_context_message("user", user_text)
        self.memory_manager.add_context_message("assistant", response)
        self.memory_manager.add_episode(
            summary="Interactive chat turn",
            raw_context_refs=["chat"],
            actions_taken=["chat_response"],
            outcome="responded",
            evidence_refs=[],
            confidence=0.8,
            tags=["chat"],
            privacy_level="internal",
        )
        return response

    @staticmethod
    def _evaluate(goal: str, action_results: list[dict[str, Any]]) -> str:
        success_count = sum(1 for result in action_results if result.get("success"))
        if success_count == len(action_results):
            return f"Goal '{goal}' progressed successfully."
        return (
            f"Goal '{goal}' partially completed with "
            f"{success_count}/{len(action_results)} successes."
        )

    @staticmethod
    def _adapt(goal: str, evaluation: str) -> str:
        if "partially" in evaluation:
            return f"Adaptation: schedule follow-up verification for goal '{goal}'."
        return f"Adaptation: reinforce successful procedure for goal '{goal}'."
