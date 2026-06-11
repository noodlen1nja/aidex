"""`aidex context` subcommands."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.table import Table

from aidex.cli.common import (
    JSON_OPTION,
    confidence_label,
    console,
    emit_json,
    fail,
)
from aidex.context import plan_context
from aidex.models import AidexError

app = typer.Typer(no_args_is_help=True, help="Plan context window usage.")


@app.command("plan")
def plan(
    file: Path = typer.Argument(
        ..., exists=True, dir_okay=False, readable=True, help="Input file."
    ),
    model: str = typer.Option("gpt-4o", "--model", "-m", help="Model id or alias."),
    reserve_output: int = typer.Option(
        4096, "--reserve-output", min=0, help="Tokens reserved for output."
    ),
    system_tokens: int = typer.Option(
        0, "--system-tokens", min=0, help="System prompt token overhead."
    ),
    json_output: bool = JSON_OPTION,
) -> None:
    """Check whether FILE fits in a model's context window."""
    try:
        text = file.read_text(encoding="utf-8")
        result = plan_context(
            text,
            model=model,
            reserve_output_tokens=reserve_output,
            system_prompt_tokens=system_tokens,
        )
    except (AidexError, OSError) as exc:
        fail(str(exc), json_output)

    if json_output:
        emit_json(result.model_dump())
        return

    table = Table(title=f"Context plan — {result.model}")
    table.add_column("Field", style="cyan")
    table.add_column("Value", justify="right")
    table.add_row("Context window", f"{result.context_window:,}")
    table.add_row("Input tokens", f"{result.input_tokens:,}")
    table.add_row("Reserved output", f"{result.reserved_output:,}")
    table.add_row("System overhead", f"{result.system_overhead:,}")
    table.add_row("Total required", f"{result.total_required:,}")
    table.add_row("Headroom", f"{result.headroom:,}")
    table.add_row("Utilization", f"{result.utilization_pct}%")
    table.add_row("Confidence", confidence_label(result.confidence))
    console.print(table)

    if result.fits:
        console.print("[bold green]✓ Fits[/bold green]")
    else:
        console.print("[bold red]✗ Does not fit[/bold red]")
        if result.suggestion is not None:
            console.print(
                f"Suggestion: chunk into ~{result.suggestion.estimated_chunks} "
                f"chunks of <= {result.suggestion.target_chunk_tokens:,} tokens."
            )
