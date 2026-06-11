"""CSV validation (named csv_module to avoid shadowing stdlib csv)."""

from __future__ import annotations

import csv as _csv
from pathlib import Path

from aidex.validate import ValidationError, ValidationIssue, ValidationResult


def validate_csv(path: str | Path, has_header: bool = True) -> ValidationResult:
    """Validate that ``path`` parses as CSV with a consistent column count.

    Column type validation is out of scope for v0.1.
    """
    file_path = Path(path)
    try:
        handle = file_path.open(encoding="utf-8", newline="")
    except OSError as exc:
        raise ValidationError(f"Failed to read {path!r}: {exc}") from exc

    errors: list[ValidationIssue] = []
    warnings: list[ValidationIssue] = []
    expected_columns: int | None = None
    row_count = 0
    header: list[str] | None = None

    with handle:
        reader = _csv.reader(handle)
        try:
            for row in reader:
                lineno = reader.line_num
                if not row:
                    warnings.append(
                        ValidationIssue(
                            line=lineno, message="Empty row", severity="warning"
                        )
                    )
                    continue
                if expected_columns is None:
                    expected_columns = len(row)
                    if has_header:
                        header = row
                        continue
                if len(row) != expected_columns:
                    errors.append(
                        ValidationIssue(
                            line=lineno,
                            column=min(len(row), expected_columns) + 1,
                            message=(
                                f"Expected {expected_columns} columns, "
                                f"got {len(row)}"
                            ),
                            severity="error",
                        )
                    )
                row_count += 1
        except _csv.Error as exc:
            errors.append(
                ValidationIssue(
                    line=reader.line_num,
                    message=f"CSV parse error: {exc}",
                    severity="error",
                )
            )

    stats: dict[str, object] = {
        "rows": row_count,
        "columns": expected_columns or 0,
    }
    if header is not None:
        stats["header"] = header

    return ValidationResult(
        valid=not errors,
        file=str(path),
        errors=errors,
        warnings=warnings,
        stats=stats,
    )
