"""JSONL (JSON Lines) validation."""

from __future__ import annotations

import json as _json
from pathlib import Path
from typing import Any

from aidex.validate import ValidationError, ValidationIssue, ValidationResult


def validate_jsonl(path: str | Path, check_keys: bool = False) -> ValidationResult:
    """Validate that every non-empty line of ``path`` is valid JSON.

    Blank lines produce warnings, not errors. With ``check_keys=True``,
    object lines whose keys differ from the first object line produce
    warnings.
    """
    file_path = Path(path)
    try:
        text = file_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValidationError(f"Failed to read {path!r}: {exc}") from exc

    errors: list[ValidationIssue] = []
    warnings: list[ValidationIssue] = []
    record_count = 0
    blank_count = 0
    reference_keys: set[str] | None = None

    for lineno, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            blank_count += 1
            warnings.append(
                ValidationIssue(line=lineno, message="Blank line", severity="warning")
            )
            continue
        try:
            record: Any = _json.loads(line)
        except _json.JSONDecodeError as exc:
            errors.append(
                ValidationIssue(
                    line=lineno,
                    column=exc.colno,
                    message=exc.msg,
                    severity="error",
                )
            )
            continue
        record_count += 1
        if check_keys and isinstance(record, dict):
            keys = set(record)
            if reference_keys is None:
                reference_keys = keys
            elif keys != reference_keys:
                missing = sorted(reference_keys - keys)
                extra = sorted(keys - reference_keys)
                details = []
                if missing:
                    details.append(f"missing: {', '.join(missing)}")
                if extra:
                    details.append(f"extra: {', '.join(extra)}")
                warnings.append(
                    ValidationIssue(
                        line=lineno,
                        message=f"Keys differ from line 1 ({'; '.join(details)})",
                        severity="warning",
                    )
                )

    return ValidationResult(
        valid=not errors,
        file=str(path),
        errors=errors,
        warnings=warnings,
        stats={"records": record_count, "blank_lines": blank_count},
    )
