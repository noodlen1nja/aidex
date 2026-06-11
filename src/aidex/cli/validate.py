"""`aidex validate` subcommands."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.markup import escape
from rich.table import Table

from aidex.cli.common import JSON_OPTION, console, emit_json, fail
from aidex.models import AidexError
from aidex.validate import ValidationResult, validate_csv, validate_json, validate_jsonl

app = typer.Typer(no_args_is_help=True, help="Validate JSON, JSONL, and CSV files.")


def _report(result: ValidationResult, json_output: bool) -> None:
    if json_output:
        emit_json(result.model_dump())
    else:
        if result.valid:
            console.print(f"[bold green]✓ VALID[/bold green] {result.file or ''}")
        else:
            console.print(f"[bold red]✗ INVALID[/bold red] {result.file or ''}")
        issues = [(i, "red") for i in result.errors] + [
            (i, "yellow") for i in result.warnings
        ]
        if issues:
            table = Table(show_header=True)
            table.add_column("Line", justify="right")
            table.add_column("Col", justify="right")
            table.add_column("Severity")
            table.add_column("Message")
            for issue, color in issues:
                table.add_row(
                    "" if issue.line is None else str(issue.line),
                    "" if issue.column is None else str(issue.column),
                    f"[{color}]{issue.severity}[/{color}]",
                    # escape: messages can quote values from the validated file
                    escape(issue.message),
                )
            console.print(table)
        if result.stats:
            stats = ", ".join(f"{k}={v}" for k, v in result.stats.items())
            console.print(f"[dim]{stats}[/dim]")
    if not result.valid:
        raise typer.Exit(1)


@app.command("json")
def json_cmd(
    file: Path = typer.Argument(
        ..., exists=True, dir_okay=False, readable=True, help="JSON file."
    ),
    schema: Path | None = typer.Option(
        None, "--schema", exists=True, dir_okay=False, help="JSON Schema file."
    ),
    json_output: bool = JSON_OPTION,
) -> None:
    """Validate a JSON file, optionally against a JSON Schema subset."""
    try:
        result = validate_json(file, schema=schema)
    except AidexError as exc:
        fail(str(exc), json_output)
    _report(result, json_output)


@app.command("jsonl")
def jsonl_cmd(
    file: Path = typer.Argument(
        ..., exists=True, dir_okay=False, readable=True, help="JSONL file."
    ),
    check_keys: bool = typer.Option(
        False, "--check-keys", help="Warn when keys differ across lines."
    ),
    json_output: bool = JSON_OPTION,
) -> None:
    """Validate a JSONL file line by line."""
    try:
        result = validate_jsonl(file, check_keys=check_keys)
    except AidexError as exc:
        fail(str(exc), json_output)
    _report(result, json_output)


@app.command("csv")
def csv_cmd(
    file: Path = typer.Argument(
        ..., exists=True, dir_okay=False, readable=True, help="CSV file."
    ),
    no_header: bool = typer.Option(
        False, "--no-header", help="Treat the first row as data, not a header."
    ),
    json_output: bool = JSON_OPTION,
) -> None:
    """Validate a CSV file for parseability and consistent column counts."""
    try:
        result = validate_csv(file, has_header=not no_header)
    except AidexError as exc:
        fail(str(exc), json_output)
    _report(result, json_output)
