"""`aidex models` subcommands."""

from __future__ import annotations

import typer
from rich.table import Table

from aidex.cli.common import (
    JSON_OPTION,
    confidence_label,
    console,
    emit_json,
    fail,
)
from aidex.models import AidexError, get_model, list_models

app = typer.Typer(no_args_is_help=True, help="Inspect the bundled model catalog.")


@app.command("list")
def list_cmd(json_output: bool = JSON_OPTION) -> None:
    """List all bundled models with pricing and context windows."""
    models = list_models()
    if json_output:
        emit_json([model.model_dump() for model in models])
        return

    table = Table(title="Bundled models")
    table.add_column("Model", style="cyan")
    table.add_column("Aliases")
    table.add_column("Context", justify="right")
    table.add_column("In $/1M", justify="right")
    table.add_column("Out $/1M", justify="right")
    table.add_column("Method")
    table.add_column("Confidence")
    for model in models:
        table.add_row(
            model.id,
            ", ".join(model.aliases),
            f"{model.context_window:,}",
            f"{model.input_price_per_1m:g}",
            f"{model.output_price_per_1m:g}",
            model.counting_method,
            confidence_label(model.confidence),
        )
    console.print(table)


@app.command("show")
def show(
    model: str = typer.Argument(..., help="Model id or alias."),
    json_output: bool = JSON_OPTION,
) -> None:
    """Show details for one model."""
    try:
        info = get_model(model)
    except AidexError as exc:
        fail(str(exc), json_output)

    if json_output:
        emit_json(info.model_dump())
        return

    table = Table(title=info.id)
    table.add_column("Field", style="cyan")
    table.add_column("Value")
    table.add_row("Aliases", ", ".join(info.aliases) or "—")
    table.add_row("Context window", f"{info.context_window:,}")
    table.add_row("Input price / 1M", f"${info.input_price_per_1m:g}")
    table.add_row("Output price / 1M", f"${info.output_price_per_1m:g}")
    table.add_row("Counting method", info.counting_method)
    table.add_row("Confidence", confidence_label(info.confidence))
    console.print(table)
