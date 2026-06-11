"""Shared CLI helpers: output formatting and error handling.

The CLI contains no business logic — it parses arguments, calls library
functions, and formats their Pydantic results.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any, NoReturn

import typer
from pydantic import BaseModel
from rich.console import Console
from rich.markup import escape

console = Console()
err_console = Console(stderr=True)

JSON_OPTION = typer.Option(
    False, "--json", help="Output machine-readable JSON instead of tables."
)


def read_text_or_file(value: str) -> str:
    """Treat ``value`` as a file path if one exists, else as literal text."""
    try:
        path = Path(value)
        if path.is_file():
            return path.read_text(encoding="utf-8")
    except OSError:
        pass
    return value


def dump(result: BaseModel | Sequence[BaseModel]) -> Any:
    if isinstance(result, BaseModel):
        return result.model_dump()
    return [item.model_dump() for item in result]


def emit_json(payload: Any) -> None:
    print(json.dumps(payload, indent=2))


def fail(message: str, json_mode: bool, code: str = "error") -> NoReturn:
    """Report a runtime error on stderr and exit 1."""
    if json_mode:
        print(json.dumps({"error": message, "code": code}), file=sys.stderr)
    else:
        # escape: messages can echo user input, which must not be parsed as markup
        err_console.print(f"[bold red]Error:[/bold red] {escape(message)}")
    raise typer.Exit(1)


def confidence_label(confidence: str) -> str:
    if confidence == "exact":
        return "[green]exact[/green]"
    return "[yellow]estimate[/yellow]"
