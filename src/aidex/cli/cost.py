"""`aidex cost` subcommands."""

from __future__ import annotations

import typer
from rich.table import Table

from aidex.cli.common import (
    JSON_OPTION,
    confidence_label,
    console,
    dump,
    emit_json,
    fail,
    read_text_or_file,
)
from aidex.cost import CostResult, estimate_cost
from aidex.models import AidexError

app = typer.Typer(no_args_is_help=True, help="Estimate costs.")


@app.command("estimate")
def estimate(
    text_or_file: str = typer.Argument(
        ..., help="Input text to price, or a path to a file."
    ),
    model: str | None = typer.Option(
        None, "--model", "-m", help="Model id or alias. Omit to compare models."
    ),
    output_tokens: int = typer.Option(
        0, "--output-tokens", min=0, help="Expected output tokens."
    ),
    json_output: bool = JSON_OPTION,
) -> None:
    """Estimate USD cost using bundled per-model pricing."""
    try:
        text = read_text_or_file(text_or_file)
        result = estimate_cost(text, model, output_tokens)
    except AidexError as exc:
        fail(str(exc), json_output)

    if json_output:
        emit_json(dump(result))
        return

    results: list[CostResult] = result if isinstance(result, list) else [result]
    table = Table(title="Cost estimates (USD)")
    table.add_column("Model", style="cyan")
    table.add_column("Input Tok", justify="right")
    table.add_column("Output Tok", justify="right")
    table.add_column("Input $", justify="right")
    table.add_column("Output $", justify="right")
    table.add_column("Total $", justify="right", style="bold")
    table.add_column("Confidence")
    for item in results:
        table.add_row(
            item.model,
            f"{item.input_tokens:,}",
            f"{item.output_tokens:,}",
            f"{item.input_cost_usd:.6f}",
            f"{item.output_cost_usd:.6f}",
            f"{item.total_cost_usd:.6f}",
            confidence_label(item.confidence),
        )
    console.print(table)
