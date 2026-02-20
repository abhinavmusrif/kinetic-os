"""CLI entrypoint for autonomous-operator."""

from __future__ import annotations

import typer

from ui.cli import commands

app = typer.Typer(help="Memory-First Autonomous Operator Platform")
memory_app = typer.Typer(help="Memory commands")
config_app = typer.Typer(help="Configuration commands")
tools_app = typer.Typer(help="Tool commands")


@app.command("chat")
def chat_cmd() -> None:
    """Interactive chat session."""
    commands.chat()


@app.command("run-goal")
def run_goal_cmd(goal: str) -> None:
    """Run a goal once."""
    commands.run_goal(goal=goal)


@memory_app.command("inspect")
def memory_inspect_cmd(limit: int = typer.Option(10, min=1, max=100)) -> None:
    """Inspect memory records."""
    commands.memory_inspect(limit=limit)


@memory_app.command("consolidate")
def memory_consolidate_cmd() -> None:
    """Run memory consolidation."""
    commands.memory_consolidate()


@config_app.command("show")
def config_show_cmd() -> None:
    """Show effective configuration."""
    commands.config_show()


@tools_app.command("list")
def tools_list_cmd() -> None:
    """List tool status."""
    commands.tools_list()


app.add_typer(memory_app, name="memory")
app.add_typer(config_app, name="config")
app.add_typer(tools_app, name="tools")


def main() -> None:
    """Console script entrypoint."""
    app()


if __name__ == "__main__":
    main()
