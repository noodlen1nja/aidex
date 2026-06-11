import json
from pathlib import Path

import pytest

from aidex.agent import (
    TOOLS,
    ToolArgumentError,
    ToolNotFoundError,
    call_tool,
    list_tools,
)

EXPECTED_TOOLS = {
    "count_tokens",
    "estimate_cost",
    "plan_context",
    "chunk_text",
    "validate_json",
    "validate_jsonl",
    "validate_csv",
    "redact_pii",
    "diff_text",
    "list_models",
}


def test_list_tools_shape() -> None:
    tools = list_tools()
    assert {t["name"] for t in tools} == EXPECTED_TOOLS
    for tool in tools:
        assert tool["description"]
        assert tool["input_schema"]["type"] == "object"


def test_tools_list_is_single_registry() -> None:
    assert {t.name for t in TOOLS} == EXPECTED_TOOLS


def test_results_are_json_serializable() -> None:
    for name, args in [
        ("count_tokens", {"text": "hello"}),
        ("estimate_cost", {"text": "hello", "output_tokens": 5}),
        ("plan_context", {"text": "hello"}),
        (
            "chunk_text",
            {"text": "hello world. " * 100, "max_tokens": 50, "overlap_tokens": 10},
        ),
        ("validate_json", {"text_or_path": '{"a": 1}'}),
        ("redact_pii", {"text": "bob@example.com"}),
        ("diff_text", {"a": "x", "b": "y"}),
        ("list_models", {}),
    ]:
        result = call_tool(name, args)
        assert isinstance(result, dict)
        json.dumps(result)  # must not raise


def test_count_tokens_single_and_comparison() -> None:
    single = call_tool("count_tokens", {"text": "hello", "model": "gpt-4o"})
    assert single["model"] == "gpt-4o"
    assert single["confidence"] == "exact"
    comparison = call_tool("count_tokens", {"text": "hello"})
    assert len(comparison["results"]) == 6


def test_validate_json_with_schema() -> None:
    result = call_tool(
        "validate_json",
        {"text_or_path": '{"a": "x"}', "schema": {"required": ["b"]}},
    )
    assert result["valid"] is False


def test_file_tools(tmp_path: Path) -> None:
    jsonl = tmp_path / "d.jsonl"
    jsonl.write_text('{"a": 1}\n', encoding="utf-8")
    csv_file = tmp_path / "d.csv"
    csv_file.write_text("a,b\n1,2\n", encoding="utf-8")
    assert call_tool("validate_jsonl", {"path": str(jsonl)})["valid"] is True
    assert call_tool("validate_csv", {"path": str(csv_file)})["valid"] is True


def test_unknown_tool_raises() -> None:
    with pytest.raises(ToolNotFoundError):
        call_tool("nope", {})


def test_missing_required_arg_raises() -> None:
    with pytest.raises(ToolArgumentError):
        call_tool("count_tokens", {})


def test_unexpected_arg_raises() -> None:
    with pytest.raises(ToolArgumentError):
        call_tool("count_tokens", {"text": "hi", "bogus": True})


def test_wrong_type_raises() -> None:
    with pytest.raises(ToolArgumentError):
        call_tool("chunk_text", {"text": "hi", "max_tokens": "lots"})
