from pathlib import Path

import pytest

from aidex.diff import DiffError, diff_text


def test_identical_strings() -> None:
    result = diff_text("same\ntext", "same\ntext")
    assert result.identical is True
    assert result.unified_diff == ""
    assert result.stats.lines_added == 0
    assert result.stats.lines_removed == 0
    assert result.token_delta is None


def test_diff_counts_lines() -> None:
    a = "one\ntwo\nthree"
    b = "one\n2\nthree\nfour"
    result = diff_text(a, b)
    assert result.identical is False
    assert result.stats.lines_added == 2  # "2" and "four"
    assert result.stats.lines_removed == 1  # "two"
    assert result.stats.chars_a == len(a)
    assert result.stats.chars_b == len(b)
    assert "@@" in result.unified_diff


def test_token_delta_with_model() -> None:
    result = diff_text("short", "a much longer piece of text", model="gpt-4o")
    assert result.token_delta is not None
    assert result.token_delta.model == "gpt-4o"
    assert result.token_delta.confidence == "exact"
    assert (
        result.token_delta.delta
        == result.token_delta.tokens_b - result.token_delta.tokens_a
    )
    assert result.token_delta.delta > 0


def test_file_inputs(tmp_path: Path) -> None:
    file_a = tmp_path / "a.txt"
    file_b = tmp_path / "b.txt"
    file_a.write_text("hello\n", encoding="utf-8")
    file_b.write_text("goodbye\n", encoding="utf-8")
    result = diff_text(file_a, file_b)
    assert result.identical is False
    assert str(file_a) in result.unified_diff
    assert str(file_b) in result.unified_diff


def test_missing_path_object_raises(tmp_path: Path) -> None:
    with pytest.raises(DiffError):
        diff_text(tmp_path / "missing.txt", "literal text")


def test_negative_context_lines_raises() -> None:
    with pytest.raises(DiffError):
        diff_text("a", "b", context_lines=-1)


def test_context_lines_respected() -> None:
    a = "\n".join(str(i) for i in range(20))
    b = a.replace("10", "ten")
    wide = diff_text(a, b, context_lines=5).unified_diff
    narrow = diff_text(a, b, context_lines=1).unified_diff
    assert len(wide.splitlines()) > len(narrow.splitlines())
