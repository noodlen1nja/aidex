"""`aidex diff` command (mounted directly on the root app)."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.markup import escape

from aidex.cli.common import JSON_OPTION, console, emit_json, fail
from aidex.diff import diff_text
from aidex.models import AidexError


def diff_command(
    file_a: Path = typer.Argument(
        ..., exists=True, dir_okay=False, readable=True, help="First file."
    ),
    file_b: Path = typer.Argument(
        ..., exists=True, dir_okay=False, readable=True, help="Second file."
    ),
    model: str | None = typer.Option(
        None, "--model", "-m", help="Include a token delta for this model."
    ),
    context: int = typer.Option(
        3, "--context", min=0, help="Context lines around changes."
    ),
    json_output: bool = JSON_OPTION,
) -> None:
    """Show a unified diff between FILE_A and FILE_B."""
    try:
        result = diff_text(file_a, file_b, context_lines=context, model=model)
    except AidexError as exc:
        fail(str(exc), json_output)

    if json_output:
        emit_json(result.model_dump())
        return

    if result.identical:
        console.print("[bold green]Files are identical.[/bold green]")
    else:
        for line in result.unified_diff.splitlines():
            # escape: diffed content is user data, not Rich markup
            text = escape(line)
            if line.startswith("+++") or line.startswith("---"):
                console.print(f"[bold]{text}[/bold]", highlight=False)
            elif line.startswith("@@"):
                console.print(f"[cyan]{text}[/cyan]", highlight=False)
            elif line.startswith("+"):
                console.print(f"[green]{text}[/green]", highlight=False)
            elif line.startswith("-"):
                console.print(f"[red]{text}[/red]", highlight=False)
            else:
                console.print(text, highlight=False)
    console.print(
        f"[dim]+{result.stats.lines_added} -{result.stats.lines_removed} "
        f"({result.stats.chars_a} → {result.stats.chars_b} chars)[/dim]"
    )
    if result.token_delta is not None:
        delta = result.token_delta
        sign = "+" if delta.delta >= 0 else ""
        console.print(
            f"[dim]Tokens ({delta.model}, {delta.confidence}): "
            f"{delta.tokens_a} → {delta.tokens_b} ({sign}{delta.delta})[/dim]"
        )
