"""`aidex chunk` subcommands."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.table import Table

from aidex.chunk import chunk_text
from aidex.cli.common import JSON_OPTION, console, dump, emit_json, fail
from aidex.models import AidexError

app = typer.Typer(no_args_is_help=True, help="Split text into chunks.")

_PREVIEW_CHARS = 40


@app.command("split")
def split(
    file: Path = typer.Argument(
        ..., exists=True, dir_okay=False, readable=True, help="Input file."
    ),
    max_tokens: int = typer.Option(
        512, "--max-tokens", min=1, help="Maximum tokens per chunk."
    ),
    overlap: int = typer.Option(
        50, "--overlap", min=0, help="Overlap tokens between chunks."
    ),
    model: str = typer.Option("gpt-4o", "--model", "-m", help="Model id or alias."),
    json_output: bool = JSON_OPTION,
) -> None:
    """Split FILE into token-bounded chunks with overlap."""
    try:
        text = file.read_text(encoding="utf-8")
        chunks = chunk_text(
            text, max_tokens=max_tokens, overlap_tokens=overlap, model=model
        )
    except (AidexError, OSError) as exc:
        fail(str(exc), json_output)

    if json_output:
        emit_json(dump(chunks))
        return

    table = Table(title=f"{len(chunks)} chunk(s) — {model}")
    table.add_column("#", justify="right")
    table.add_column("Tokens", justify="right")
    table.add_column("Span", justify="right")
    table.add_column("Preview")
    for chunk in chunks:
        preview = chunk.text[:_PREVIEW_CHARS].replace("\n", "\\n")
        if len(chunk.text) > _PREVIEW_CHARS:
            preview += "…"
        table.add_row(
            str(chunk.index),
            f"{chunk.token_count:,}",
            f"{chunk.start_char}–{chunk.end_char}",
            preview,
        )
    console.print(table)
