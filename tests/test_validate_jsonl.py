from pathlib import Path

import pytest

from aidex.validate import ValidationError
from aidex.validate.jsonl import validate_jsonl


def test_valid_jsonl(tmp_path: Path) -> None:
    path = tmp_path / "data.jsonl"
    path.write_text('{"a": 1}\n{"a": 2}\n{"a": 3}\n', encoding="utf-8")
    result = validate_jsonl(path)
    assert result.valid is True
    assert result.stats["records"] == 3


def test_invalid_line_reports_line_number(tmp_path: Path) -> None:
    path = tmp_path / "data.jsonl"
    path.write_text('{"a": 1}\nnot json\n{"a": 3}\n', encoding="utf-8")
    result = validate_jsonl(path)
    assert result.valid is False
    assert len(result.errors) == 1
    assert result.errors[0].line == 2


def test_blank_lines_warn_but_pass(tmp_path: Path) -> None:
    path = tmp_path / "data.jsonl"
    path.write_text('{"a": 1}\n\n{"a": 2}\n', encoding="utf-8")
    result = validate_jsonl(path)
    assert result.valid is True
    assert len(result.warnings) == 1
    assert result.warnings[0].line == 2
    assert result.stats["blank_lines"] == 1


def test_check_keys_warns_on_mismatch(tmp_path: Path) -> None:
    path = tmp_path / "data.jsonl"
    path.write_text('{"a": 1, "b": 2}\n{"a": 1, "c": 3}\n', encoding="utf-8")
    result = validate_jsonl(path, check_keys=True)
    assert result.valid is True  # key drift is a warning, not an error
    assert any("Keys differ" in w.message for w in result.warnings)
    assert result.warnings[0].line == 2


def test_check_keys_silent_when_consistent(tmp_path: Path) -> None:
    path = tmp_path / "data.jsonl"
    path.write_text('{"a": 1}\n{"a": 2}\n', encoding="utf-8")
    result = validate_jsonl(path, check_keys=True)
    assert result.warnings == []


def test_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(ValidationError):
        validate_jsonl(tmp_path / "missing.jsonl")
