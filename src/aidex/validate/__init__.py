"""Validators for JSON, JSONL, and CSV files.

All validators share :class:`ValidationResult`. Invalid content is
reported in the result, not raised; :class:`ValidationError` is reserved
for problems running the validation itself (unreadable file, bad schema).
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from aidex.models import AidexError


class ValidationError(AidexError):
    """Raised when validation cannot run (unreadable input, bad schema)."""


class ValidationIssue(BaseModel):
    """One error or warning found during validation."""

    line: int | None = None
    column: int | None = None
    message: str
    severity: Literal["error", "warning"]


class ValidationResult(BaseModel):
    """Shared result shape for all validators."""

    valid: bool
    file: str | None = None
    errors: list[ValidationIssue] = Field(default_factory=list)
    warnings: list[ValidationIssue] = Field(default_factory=list)
    stats: dict[str, Any] = Field(default_factory=dict)


from aidex.validate.csv_module import validate_csv  # noqa: E402
from aidex.validate.json import validate_json  # noqa: E402
from aidex.validate.jsonl import validate_jsonl  # noqa: E402

__all__ = [
    "ValidationError",
    "ValidationIssue",
    "ValidationResult",
    "validate_csv",
    "validate_json",
    "validate_jsonl",
]
