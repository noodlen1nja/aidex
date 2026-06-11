"""Strict JSON validation with optional JSON Schema checking.

JSON syntax is strict: no trailing commas, no comments. Schema validation
supports a practical subset of JSON Schema implemented without extra
dependencies: ``type``, ``properties``, ``required``, ``items``, ``enum``,
``additionalProperties`` (boolean), ``minimum``, ``maximum``,
``minLength``, and ``maxLength``. Unsupported keywords are ignored.
"""

from __future__ import annotations

import json as _json
from pathlib import Path
from typing import Any

from aidex.validate import ValidationError, ValidationIssue, ValidationResult

_TYPE_CHECKS: dict[str, type | tuple[type, ...]] = {
    "object": dict,
    "array": list,
    "string": str,
    "boolean": bool,
    "null": type(None),
}


def _resolve_input(text_or_path: str | Path) -> tuple[str, str | None]:
    """Return (text, file_label). Paths and strings naming an existing file
    are read from disk; other strings are treated as literal JSON text."""
    path = Path(text_or_path)
    try:
        is_file = path.is_file()
    except (OSError, ValueError):
        is_file = False  # not a usable path (e.g. too long) -> literal text
    if is_file:
        try:
            return path.read_text(encoding="utf-8"), str(text_or_path)
        except OSError as exc:
            raise ValidationError(f"Failed to read {text_or_path!r}: {exc}") from exc
    if isinstance(text_or_path, Path):
        raise ValidationError(f"File not found: {text_or_path}")
    return text_or_path, None


def _check_type(instance: Any, expected: str) -> bool:
    if expected == "integer":
        return isinstance(instance, int) and not isinstance(instance, bool)
    if expected == "number":
        return isinstance(instance, (int, float)) and not isinstance(instance, bool)
    check = _TYPE_CHECKS.get(expected)
    return check is not None and isinstance(instance, check)


def _check_schema(instance: Any, schema: dict[str, Any], path: str) -> list[str]:
    errors: list[str] = []
    expected_type = schema.get("type")
    if expected_type is not None:
        types = expected_type if isinstance(expected_type, list) else [expected_type]
        if not any(_check_type(instance, t) for t in types):
            errors.append(
                f"{path}: expected type {' or '.join(types)}, "
                f"got {type(instance).__name__}"
            )
            return errors
    if "enum" in schema and instance not in schema["enum"]:
        errors.append(f"{path}: value {instance!r} not in enum {schema['enum']!r}")
    if isinstance(instance, str):
        min_len, max_len = schema.get("minLength"), schema.get("maxLength")
        if min_len is not None and len(instance) < min_len:
            errors.append(f"{path}: string shorter than minLength {min_len}")
        if max_len is not None and len(instance) > max_len:
            errors.append(f"{path}: string longer than maxLength {max_len}")
    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        minimum, maximum = schema.get("minimum"), schema.get("maximum")
        if minimum is not None and instance < minimum:
            errors.append(f"{path}: {instance} is less than minimum {minimum}")
        if maximum is not None and instance > maximum:
            errors.append(f"{path}: {instance} is greater than maximum {maximum}")
    if isinstance(instance, dict):
        properties = schema.get("properties", {})
        for key in schema.get("required", []):
            if key not in instance:
                errors.append(f"{path}: missing required property {key!r}")
        for key, sub_schema in properties.items():
            if key in instance and isinstance(sub_schema, dict):
                errors.extend(_check_schema(instance[key], sub_schema, f"{path}.{key}"))
        if schema.get("additionalProperties") is False:
            for key in instance:
                if key not in properties:
                    errors.append(f"{path}: unexpected property {key!r}")
    if isinstance(instance, list):
        items = schema.get("items")
        if isinstance(items, dict):
            for i, item in enumerate(instance):
                errors.extend(_check_schema(item, items, f"{path}[{i}]"))
    return errors


def validate_json(
    text_or_path: str | Path, schema: dict[str, Any] | str | Path | None = None
) -> ValidationResult:
    """Validate JSON syntax and, optionally, a JSON Schema subset.

    ``schema`` may be a schema dict or a path to a schema file.
    """
    text, file_label = _resolve_input(text_or_path)

    schema_dict: dict[str, Any] | None = None
    if isinstance(schema, dict):
        schema_dict = schema
    elif schema is not None:
        schema_text, _ = _resolve_input(schema)
        try:
            loaded = _json.loads(schema_text)
        except (_json.JSONDecodeError, RecursionError) as exc:
            raise ValidationError(f"Schema is not valid JSON: {exc}") from exc
        if not isinstance(loaded, dict):
            raise ValidationError("Schema must be a JSON object")
        schema_dict = loaded

    errors: list[ValidationIssue] = []
    stats: dict[str, Any] = {"bytes": len(text.encode("utf-8"))}
    try:
        instance = _json.loads(text)
    except _json.JSONDecodeError as exc:
        errors.append(
            ValidationIssue(
                line=exc.lineno,
                column=exc.colno,
                message=exc.msg,
                severity="error",
            )
        )
        return ValidationResult(
            valid=False, file=file_label, errors=errors, stats=stats
        )
    except RecursionError:
        errors.append(
            ValidationIssue(
                message="JSON is nested too deeply to parse", severity="error"
            )
        )
        return ValidationResult(
            valid=False, file=file_label, errors=errors, stats=stats
        )

    stats["top_level_type"] = type(instance).__name__
    if schema_dict is not None:
        stats["schema_checked"] = True
        try:
            for message in _check_schema(instance, schema_dict, "$"):
                errors.append(ValidationIssue(message=message, severity="error"))
        except RecursionError:
            errors.append(
                ValidationIssue(
                    message="JSON is nested too deeply to check against the schema",
                    severity="error",
                )
            )

    return ValidationResult(
        valid=not errors, file=file_label, errors=errors, stats=stats
    )
