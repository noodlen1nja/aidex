from pathlib import Path

import pytest

from aidex.validate import ValidationError
from aidex.validate.csv_module import validate_csv


def test_valid_csv(tmp_path: Path) -> None:
    path = tmp_path / "data.csv"
    path.write_text("name,age\nalice,30\nbob,41\n", encoding="utf-8")
    result = validate_csv(path)
    assert result.valid is True
    assert result.stats["rows"] == 2
    assert result.stats["columns"] == 2
    assert result.stats["header"] == ["name", "age"]


def test_inconsistent_columns_reports_row(tmp_path: Path) -> None:
    path = tmp_path / "data.csv"
    path.write_text("a,b,c\n1,2,3\n1,2\n1,2,3,4\n", encoding="utf-8")
    result = validate_csv(path)
    assert result.valid is False
    assert len(result.errors) == 2
    assert result.errors[0].line == 3
    assert "Expected 3 columns, got 2" in result.errors[0].message
    assert result.errors[1].line == 4


def test_no_header_mode(tmp_path: Path) -> None:
    path = tmp_path / "data.csv"
    path.write_text("1,2\n3,4\n", encoding="utf-8")
    result = validate_csv(path, has_header=False)
    assert result.valid is True
    assert result.stats["rows"] == 2
    assert "header" not in result.stats


def test_quoted_fields_with_commas(tmp_path: Path) -> None:
    path = tmp_path / "data.csv"
    path.write_text('name,quote\nalice,"hello, world"\n', encoding="utf-8")
    result = validate_csv(path)
    assert result.valid is True
    assert result.stats["rows"] == 1


def test_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(ValidationError):
        validate_csv(tmp_path / "missing.csv")
