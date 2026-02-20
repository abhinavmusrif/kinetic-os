"""CLI entrypoint for autonomous-operator."""

from __future__ import annotations

import typer

from ui.cli import commands

app = typer.Typer(help="Memory-First Autonomous Operator Platform")
memory_app = typer.Typer(help="Memory commands")
config_app = typer.Typer(help="Configuration commands")
tools_app = typer.Typer(help="Tool commands")
goals_app = typer.Typer(help="Goal commands")
self_model_app = typer.Typer(help="Self-Model commands")


@app.command("chat")
def chat_cmd() -> None:
    """Interactive chat session."""
    commands.chat()


@app.command("run-goal")
def run_goal_cmd(goal: str) -> None:
    """Run a goal once."""
    commands.run_goal(goal=goal)


@memory_app.command("add")
def memory_add_cmd(
    text: str = typer.Argument(..., help="Memory text content"),
    source: str = typer.Option("cli", help="Source of memory"),
    outcome: str = typer.Option("success", help="Outcome of the memory event")
) -> None:
    """Add a new episodic memory manually."""
    commands.memory_add(text=text, source=source, outcome=outcome)


@memory_app.command("inspect")
def memory_inspect_cmd(
    limit: int = typer.Option(10, min=1, max=100),
    claims: bool = typer.Option(False, "--claims", help="Only show claims"),
    episodes: bool = typer.Option(False, "--episodes", help="Only show episodes"),
    procedures: bool = typer.Option(False, "--procedures", help="Only show procedures"),
    goals: bool = typer.Option(False, "--goals", help="Only show goals"),
) -> None:
    """Inspect memory records."""
    commands.memory_inspect(limit=limit, claims=claims, episodes=episodes, procedures=procedures, goals=goals)


@memory_app.command("consolidate")
def memory_consolidate_cmd(
    mode: str = typer.Option("light", "--mode", help="Consolidation mode: light or deep")
) -> None:
    """Run memory consolidation."""
    commands.memory_consolidate(mode=mode)


@config_app.command("show")
def config_show_cmd() -> None:
    """Show effective configuration."""
    commands.config_show()


@tools_app.command("list")
def tools_list_cmd() -> None:
    """List tool status."""
    commands.tools_list()


@goals_app.command("add")
def goals_add_cmd(
    goal: str = typer.Argument(..., help="Goal description text"),
    priority: int = typer.Option(5, help="Goal priority (1-10)"),
) -> None:
    """Add a new goal."""
    commands.goals_add(goal=goal, priority=priority)


@goals_app.command("list")
def goals_list_cmd(limit: int = typer.Option(10)) -> None:
    """List goals."""
    commands.goals_list(limit=limit)


@self_model_app.command("show")
def self_model_show_cmd() -> None:
    """Show self-model."""
    commands.self_model_show()


app.add_typer(memory_app, name="memory")
app.add_typer(config_app, name="config")
app.add_typer(tools_app, name="tools")
app.add_typer(goals_app, name="goals")
app.add_typer(self_model_app, name="self-model")


def main() -> None:
    """Console script entrypoint."""
    app()


if __name__ == "__main__":
    main()
