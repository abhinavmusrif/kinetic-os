"""Typer command handlers."""

from __future__ import annotations

import json
from pathlib import Path

import typer

from core.orchestrator import Orchestrator, RuntimeBundle


def _runtime(root: Path | None = None) -> RuntimeBundle:
    bundle = Orchestrator(root=root).build()
    return bundle


def run_goal(goal: str) -> None:
    """Run one goal execution cycle."""
    bundle = _runtime()
    result = bundle.control_loop.run_goal(goal)
    consolidation = bundle.consolidator.run()
    candidate_beliefs = consolidation.get("replay", {}).get("extracted_claims", [])
    stored_claims = bundle.memory.list_semantic_claims(limit=5)

    typer.echo(f"Goal: {result.goal}")
    typer.echo(f"Tasks: {len(result.tasks_executed)}")
    for task in result.tasks_executed:
        typer.echo(f"- {task}")
    typer.echo(f"Iterations: {result.iterations} | Completed: {result.completed}")
    typer.echo(f"Evaluation: {result.evaluation}")
    typer.echo(f"Adaptation: {result.adaptation}")
    typer.echo(f"Consolidation proposals: {len(candidate_beliefs)}")
    if stored_claims:
        latest = stored_claims[0]
        typer.echo(
            "Latest semantic claim: "
            f"{latest.get('claim', '')} | confidence={latest.get('confidence', 0.0):.2f}"
        )


def chat() -> None:
    """Run interactive chat loop."""
    bundle = _runtime()
    typer.echo("Chat mode. Type 'exit' to quit.")
    while True:
        user_text = typer.prompt("you")
        if user_text.strip().lower() in {"exit", "quit"}:
            typer.echo("bye")
            break
        response = bundle.control_loop.handle_chat_turn(user_text=user_text, llm=bundle.llm)
        typer.echo(f"assistant: {response}")


def memory_add(text: str, source: str, outcome: str) -> None:
    """Add an episodic memory."""
    bundle = _runtime()
    bundle.memory.add_episode(
        text=text,
        structured_json={},
        source=source,
        outcome=outcome,
        evidence_refs=[],
        confidence=1.0,
        privacy_level="internal"
    )
    typer.echo(f"Added episodic memory: {text}")


def memory_inspect(limit: int = 10, claims: bool = False, episodes: bool = False, procedures: bool = False, goals: bool = False) -> None:
    """Inspect recent memory records."""
    bundle = _runtime()
    
    if claims or episodes or procedures or goals:
        data = {}
        if claims:
            data["claims"] = bundle.memory.list_semantic_claims(limit=limit)
        if episodes:
            data["episodes"] = bundle.memory.list_episodes(limit=limit)
        if procedures:
            data["procedures"] = bundle.memory.list_procedures(limit=limit)
        if goals:
            data["goals"] = bundle.memory.list_goals(limit=limit)
        typer.echo(json.dumps(_json_safe(data), indent=2))
        return
        
    data = bundle.memory.inspect_recent(limit=limit)
    typer.echo(json.dumps(_json_safe(data), indent=2))


def memory_consolidate(mode: str = "light") -> None:
    """Run consolidation cycle."""
    bundle = _runtime()
    result = bundle.consolidator.run(mode=mode)
    typer.echo(json.dumps(_json_safe(result), indent=2))


def goals_add(goal: str, priority: int) -> None:
    """Add a new goal."""
    bundle = _runtime()
    bundle.memory.add_goal(goal_text=goal, priority=priority, progress_state="pending")
    typer.echo(f"Added goal: {goal}")


def goals_list(limit: int) -> None:
    """List goals."""
    bundle = _runtime()
    goals = bundle.memory.list_goals(limit=limit)
    typer.echo(json.dumps(_json_safe(goals), indent=2))


def self_model_show() -> None:
    """Show self model."""
    bundle = _runtime()
    model = bundle.memory.get_self_model()
    typer.echo(json.dumps(_json_safe(model), indent=2))


def config_show() -> None:
    """Show effective runtime config."""
    bundle = _runtime()
    typer.echo(json.dumps(_json_safe(bundle.config), indent=2))


def tools_list() -> None:
    """List tools and enabled flags."""
    bundle = _runtime()
    for tool in bundle.tool_registry.list_tools():
        typer.echo(f"{tool.name}: {'enabled' if tool.enabled else 'disabled'}")


def _json_safe(payload: object) -> object:
    """Convert datetimes to strings for JSON output."""
    if isinstance(payload, dict):
        return {k: _json_safe(v) for k, v in payload.items()}
    if isinstance(payload, list):
        return [_json_safe(v) for v in payload]
    if hasattr(payload, "isoformat"):
        try:
            return payload.isoformat()
        except Exception:
            return str(payload)
    return payload
