"""`aidex tokens` subcommands."""

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
from aidex.models import AidexError
from aidex.tokens import TokenCountResult, count_tokens

app = typer.Typer(no_args_is_help=True, help="Count tokens.")


@app.command("count")
def count(
    text_or_file: str = typer.Argument(..., help="Text to count, or a path to a file."),
    model: str | None = typer.Option(
        None, "--model", "-m", help="Model id or alias. Omit to compare models."
    ),
    json_output: bool = JSON_OPTION,
) -> None:
    """Count tokens for one model or across the default comparison set."""
    try:
        text = read_text_or_file(text_or_file)
        result = count_tokens(text, model)
    except AidexError as exc:
        fail(str(exc), json_output)

    if json_output:
        emit_json(dump(result))
        return

    results: list[TokenCountResult] = result if isinstance(result, list) else [result]
    table = Table(title="Token counts")
    table.add_column("Model", style="cyan")
    table.add_column("Tokens", justify="right")
    table.add_column("Method")
    table.add_column("Confidence")
    for item in results:
        table.add_row(
            item.model,
            f"{item.token_count:,}",
            item.counting_method,
            confidence_label(item.confidence),
        )
    console.print(table)
