"""`aidex tools` subcommands."""

from __future__ import annotations

import typer
from rich.table import Table

from aidex.agent import list_tools
from aidex.cli.common import JSON_OPTION, console, emit_json

app = typer.Typer(no_args_is_help=True, help="Inspect the agent tool registry.")


@app.command("list")
def list_cmd(json_output: bool = JSON_OPTION) -> None:
    """List all registered agent tools."""
    tools = list_tools()
    if json_output:
        emit_json(tools)
        return

    table = Table(title="Agent tools")
    table.add_column("Tool", style="cyan")
    table.add_column("Description")
    for tool in tools:
        table.add_row(tool["name"], tool["description"])
    console.print(table)
