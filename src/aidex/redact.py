"""Regex-based PII redaction.

Redaction is one-way: there is no unredact, and the audit trail records
only the PII type, character span, and placeholder — never the original
value. v0.1 is regex-only; NER-based detection (names, addresses) is out
of scope.
"""

from __future__ import annotations

import re
from re import Pattern

from pydantic import BaseModel

from aidex.models import AidexError

PLACEHOLDER_STYLES = ("tagged", "generic")

#: Built-in pattern names, in match-priority order (earlier wins on overlap).
_PATTERNS: dict[str, tuple[Pattern[str], str]] = {
    "api_key": (
        re.compile(
            r"\b(?:sk-[A-Za-z0-9_-]{16,}|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{36,})\b"
        ),
        "[API_KEY]",
    ),
    "email": (
        re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
        "[EMAIL]",
    ),
    "ssn": (
        re.compile(r"(?<!\d)\d{3}-\d{2}-\d{4}(?!\d)"),
        "[SSN]",
    ),
    "credit_card": (
        re.compile(r"(?<!\d)\d{4}[ -]?\d{4}[ -]?\d{4}[ -]?\d{4}(?!\d)"),
        "[CREDIT_CARD]",
    ),
    "ipv4": (
        re.compile(r"(?<!\d)(?:\d{1,3}\.){3}\d{1,3}(?!\d)"),
        "[IP]",
    ),
    "phone": (
        re.compile(
            r"(?<!\d)(?:\+?\d{1,2}[-.\s]?)?(?:\(\d{3}\)|\d{3})[-.\s]?\d{3}[-.\s]?\d{4}(?!\d)"
        ),
        "[PHONE]",
    ),
}

BUILTIN_PATTERNS: tuple[str, ...] = tuple(_PATTERNS)


class RedactionError(AidexError):
    """Raised for unknown pattern names or placeholder styles."""


class Redaction(BaseModel):
    """Audit record for one redacted span. Never contains the original value."""

    type: str
    start: int
    end: int
    placeholder: str


class RedactionResult(BaseModel):
    """Redacted text plus a one-way audit trail."""

    redacted_text: str
    redactions: list[Redaction]
    redaction_count: int


def redact_pii(
    text: str,
    patterns: list[str] | None = None,
    placeholder_style: str = "tagged",
) -> RedactionResult:
    """Redact PII from ``text`` using built-in regex patterns.

    ``patterns`` selects a subset of :data:`BUILTIN_PATTERNS`; ``None``
    applies all of them. ``placeholder_style`` is ``"tagged"`` (typed
    placeholders like ``[EMAIL]``) or ``"generic"`` (``[REDACTED]``).
    Spans in the audit trail refer to positions in the original text.
    """
    if placeholder_style not in PLACEHOLDER_STYLES:
        raise RedactionError(
            f"Unknown placeholder_style {placeholder_style!r}. "
            f"Choose from: {', '.join(PLACEHOLDER_STYLES)}"
        )
    selected = list(_PATTERNS) if patterns is None else patterns
    unknown = [name for name in selected if name not in _PATTERNS]
    if unknown:
        raise RedactionError(
            f"Unknown pattern(s): {', '.join(unknown)}. "
            f"Built-in patterns: {', '.join(BUILTIN_PATTERNS)}"
        )

    # Priority follows _PATTERNS order so e.g. api_key beats phone on overlap.
    matches: list[tuple[int, int, int, str, str]] = []
    for priority, name in enumerate(n for n in _PATTERNS if n in selected):
        regex, tag = _PATTERNS[name]
        for m in regex.finditer(text):
            matches.append((m.start(), -(m.end() - m.start()), priority, name, tag))
    matches.sort()

    chosen: list[tuple[int, int, str, str]] = []
    last_end = 0
    for start, neg_len, _priority, name, tag in matches:
        end = start - neg_len
        if start >= last_end:
            chosen.append((start, end, name, tag))
            last_end = end

    redactions: list[Redaction] = []
    out: list[str] = []
    cursor = 0
    for start, end, name, tag in chosen:
        placeholder = tag if placeholder_style == "tagged" else "[REDACTED]"
        out.append(text[cursor:start])
        out.append(placeholder)
        cursor = end
        redactions.append(
            Redaction(type=name, start=start, end=end, placeholder=placeholder)
        )
    out.append(text[cursor:])

    return RedactionResult(
        redacted_text="".join(out),
        redactions=redactions,
        redaction_count=len(redactions),
    )
