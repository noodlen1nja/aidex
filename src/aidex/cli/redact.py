"""`aidex redact` subcommands."""

from __future__ import annotations

import typer
from rich.table import Table

from aidex.cli.common import (
    JSON_OPTION,
    console,
    emit_json,
    fail,
    read_text_or_file,
)
from aidex.models import AidexError
from aidex.redact import redact_pii

app = typer.Typer(no_args_is_help=True, help="Redact PII from text.")


@app.command("pii")
def pii(
    text_or_file: str = typer.Argument(
        ..., help="Text to redact, or a path to a file."
    ),
    patterns: str | None = typer.Option(
        None,
        "--patterns",
        help="Comma-separated pattern names (e.g. email,phone,api_key). "
        "Omit for all built-ins.",
    ),
    placeholder_style: str = typer.Option(
        "tagged", "--placeholder-style", help="'tagged' or 'generic'."
    ),
    json_output: bool = JSON_OPTION,
) -> None:
    """Redact emails, phones, SSNs, credit cards, IPs, and API keys."""
    try:
        text = read_text_or_file(text_or_file)
        selected = (
            [p.strip() for p in patterns.split(",") if p.strip()] if patterns else None
        )
        result = redact_pii(
            text, patterns=selected, placeholder_style=placeholder_style
        )
    except AidexError as exc:
        fail(str(exc), json_output)

    if json_output:
        emit_json(result.model_dump())
        return

    console.print(result.redacted_text)
    if result.redactions:
        table = Table(title=f"{result.redaction_count} redaction(s)")
        table.add_column("Type", style="cyan")
        table.add_column("Span", justify="right")
        table.add_column("Placeholder")
        for redaction in result.redactions:
            table.add_row(
                redaction.type,
                f"{redaction.start}–{redaction.end}",
                redaction.placeholder,
            )
        console.print(table)
    else:
        console.print("[dim]No PII found.[/dim]")
