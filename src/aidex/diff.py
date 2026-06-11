"""Text diffing via stdlib difflib, with optional token delta."""

from __future__ import annotations

import difflib
from pathlib import Path

from pydantic import BaseModel

from aidex.models import AidexError, Confidence, get_model
from aidex.tokens import count_for_model


class DiffError(AidexError):
    """Raised when diff inputs cannot be read."""


class DiffStats(BaseModel):
    """Line and character statistics for a diff."""

    lines_added: int
    lines_removed: int
    chars_a: int
    chars_b: int


class TokenDelta(BaseModel):
    """Token count difference between the two inputs for one model."""

    tokens_a: int
    tokens_b: int
    delta: int
    model: str
    confidence: Confidence


class DiffResult(BaseModel):
    """Unified diff between two texts or files."""

    identical: bool
    unified_diff: str
    stats: DiffStats
    token_delta: TokenDelta | None = None


def _read_input(value: str | Path, label: str) -> tuple[str, str]:
    """Return (text, display_label). Path inputs and strings naming an
    existing file are read from disk; other strings are literal text."""
    path = Path(value)
    try:
        is_file = path.is_file()
    except (OSError, ValueError):
        is_file = False  # not a usable path (e.g. too long) -> literal text
    if is_file:
        try:
            return path.read_text(encoding="utf-8"), str(value)
        except OSError as exc:
            raise DiffError(f"Failed to read {value!r}: {exc}") from exc
    if isinstance(value, Path):
        raise DiffError(f"File not found: {value}")
    return value, label


def diff_text(
    a: str | Path,
    b: str | Path,
    context_lines: int = 3,
    model: str | None = None,
) -> DiffResult:
    """Compute a unified diff between ``a`` and ``b``.

    Inputs may be literal strings or paths to files. With ``model`` set,
    a token delta for that model is included.
    """
    if context_lines < 0:
        raise DiffError("context_lines must be >= 0")
    text_a, label_a = _read_input(a, "a")
    text_b, label_b = _read_input(b, "b")

    diff_lines = list(
        difflib.unified_diff(
            text_a.splitlines(),
            text_b.splitlines(),
            fromfile=label_a,
            tofile=label_b,
            n=context_lines,
            lineterm="",
        )
    )
    lines_added = sum(
        1 for line in diff_lines if line.startswith("+") and not line.startswith("+++")
    )
    lines_removed = sum(
        1 for line in diff_lines if line.startswith("-") and not line.startswith("---")
    )

    token_delta: TokenDelta | None = None
    if model is not None:
        info = get_model(model)
        tokens_a = count_for_model(text_a, info).token_count
        tokens_b = count_for_model(text_b, info).token_count
        token_delta = TokenDelta(
            tokens_a=tokens_a,
            tokens_b=tokens_b,
            delta=tokens_b - tokens_a,
            model=info.id,
            confidence=info.confidence,
        )

    return DiffResult(
        identical=text_a == text_b,
        unified_diff="\n".join(diff_lines),
        stats=DiffStats(
            lines_added=lines_added,
            lines_removed=lines_removed,
            chars_a=len(text_a),
            chars_b=len(text_b),
        ),
        token_delta=token_delta,
    )
