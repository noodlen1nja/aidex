from pathlib import Path

import pytest

from aidex.validate import ValidationError
from aidex.validate.json import validate_json


def test_valid_json_text() -> None:
    result = validate_json('{"a": 1, "b": [true, null]}')
    assert result.valid is True
    assert result.errors == []
    assert result.file is None
    assert result.stats["top_level_type"] == "dict"


def test_invalid_json_reports_line_and_column() -> None:
    result = validate_json('{\n  "a": 1,\n}')  # trailing comma is strict-invalid
    assert result.valid is False
    # exact position varies by Python version; it must point at line 2 or 3
    assert result.errors[0].line in (2, 3)
    assert result.errors[0].column is not None
    assert result.errors[0].severity == "error"


def test_json_file_input(tmp_path: Path) -> None:
    path = tmp_path / "data.json"
    path.write_text('{"name": "aidex"}', encoding="utf-8")
    result = validate_json(path)
    assert result.valid is True
    assert result.file == str(path)


def test_missing_path_object_raises(tmp_path: Path) -> None:
    with pytest.raises(ValidationError):
        validate_json(tmp_path / "nope.json")


def test_schema_pass() -> None:
    schema = {
        "type": "object",
        "required": ["name"],
        "properties": {
            "name": {"type": "string", "minLength": 2},
            "count": {"type": "integer", "minimum": 0},
        },
    }
    result = validate_json('{"name": "aidex", "count": 3}', schema=schema)
    assert result.valid is True
    assert result.stats["schema_checked"] is True


def test_schema_violations_reported() -> None:
    schema = {
        "type": "object",
        "required": ["name", "kind"],
        "properties": {
            "name": {"type": "string"},
            "kind": {"enum": ["a", "b"]},
            "count": {"type": "integer", "maximum": 10},
        },
        "additionalProperties": False,
    }
    result = validate_json('{"name": 5, "count": 99, "junk": 1}', schema=schema)
    assert result.valid is False
    messages = " | ".join(e.message for e in result.errors)
    assert "kind" in messages  # missing required
    assert "expected type string" in messages
    assert "maximum" in messages
    assert "junk" in messages  # additionalProperties: false


def test_schema_array_items() -> None:
    schema = {"type": "array", "items": {"type": "integer"}}
    assert validate_json("[1, 2, 3]", schema=schema).valid is True
    assert validate_json('[1, "x"]', schema=schema).valid is False


def test_schema_from_file(tmp_path: Path) -> None:
    schema_path = tmp_path / "schema.json"
    schema_path.write_text('{"type": "object"}', encoding="utf-8")
    assert validate_json('{"a": 1}', schema=schema_path).valid is True
    assert validate_json("[1]", schema=schema_path).valid is False


def test_bad_schema_raises(tmp_path: Path) -> None:
    schema_path = tmp_path / "schema.json"
    schema_path.write_text("not json", encoding="utf-8")
    with pytest.raises(ValidationError):
        validate_json('{"a": 1}', schema=schema_path)
    schema_path.write_text("[1, 2]", encoding="utf-8")
    with pytest.raises(ValidationError):
        validate_json('{"a": 1}', schema=schema_path)
