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
    candidate_beliefs = consolidation.get("replay", {}).get("candidate_beliefs", [])
    stored_beliefs = bundle.memory.list_beliefs(limit=5)

    typer.echo(f"Goal: {result.goal}")
    typer.echo(f"Tasks: {len(result.tasks)}")
    for task in result.tasks:
        typer.echo(f"- {task}")
    typer.echo(f"Evaluation: {result.evaluation}")
    typer.echo(f"Adaptation: {result.adaptation}")
    typer.echo(f"Consolidation proposals: {len(candidate_beliefs)}")
    if stored_beliefs:
        latest = stored_beliefs[0]
        typer.echo(
            "Latest belief: "
            f"{latest['claim']} | confidence={latest['confidence']:.2f} | status={latest['status']}"
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


def memory_inspect(limit: int = 10) -> None:
    """Inspect recent memory records."""
    bundle = _runtime()
    data = bundle.memory.inspect_recent(limit=limit)
    typer.echo(json.dumps(_json_safe(data), indent=2))


def memory_consolidate() -> None:
    """Run consolidation cycle."""
    bundle = _runtime()
    result = bundle.consolidator.run()
    typer.echo(json.dumps(_json_safe(result), indent=2))


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
