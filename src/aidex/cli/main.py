"""Root Typer application. Mounts all subcommands; contains no business logic."""

from __future__ import annotations

import os
from pathlib import Path

import typer

from aidex import __version__
from aidex.cli import (
    chunk,
    context_cmd,
    cost,
    models_cmd,
    redact,
    tokens,
    tools_cmd,
    validate,
)
from aidex.cli.common import err_console
from aidex.cli.diff import diff_command
from aidex.models import ENV_MODELS_FILE, load_catalog

app = typer.Typer(
    name="aidex-tools",
    help="Aidex — offline AI developer tooling.",
    no_args_is_help=True,
)

app.add_typer(tokens.app, name="tokens")
app.add_typer(cost.app, name="cost")
app.add_typer(context_cmd.app, name="context")
app.add_typer(chunk.app, name="chunk")
app.add_typer(validate.app, name="validate")
app.add_typer(redact.app, name="redact")
app.add_typer(models_cmd.app, name="models")
app.add_typer(tools_cmd.app, name="tools")
app.command("diff")(diff_command)

mcp_app = typer.Typer(no_args_is_help=True, help="MCP server (stub in v0.1).")


@mcp_app.command("serve")
def mcp_serve() -> None:
    """Stub: the MCP server ships in a future release."""
    err_console.print(
        "The MCP server is not implemented in v0.1. "
        "Use the agent registry instead: from aidex.agent import list_tools, call_tool"
    )
    raise typer.Exit(1)


app.add_typer(mcp_app, name="mcp")


def _version_callback(value: bool) -> None:
    if value:
        print(f"aidex-tools {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
    models_file: Path | None = typer.Option(
        None,
        "--models-file",
        exists=True,
        dir_okay=False,
        readable=True,
        help="External models.json that overrides bundled pricing "
        f"(equivalent to setting ${ENV_MODELS_FILE}).",
    ),
) -> None:
    """Aidex — offline AI developer tooling."""
    if models_file is not None:
        os.environ[ENV_MODELS_FILE] = str(models_file)
        # the catalog may have been cached during import; force a reload
        load_catalog.cache_clear()


if __name__ == "__main__":
    app()
