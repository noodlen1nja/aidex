import json
from pathlib import Path

from typer.testing import CliRunner

from aidex.cli.main import app

runner = CliRunner()


def test_help() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "aidex" in result.output.lower()


def test_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


def test_tokens_count_human() -> None:
    result = runner.invoke(app, ["tokens", "count", "hello world"])
    assert result.exit_code == 0
    assert "Confidence" in result.output


def test_tokens_count_json_single() -> None:
    result = runner.invoke(
        app, ["tokens", "count", "hello world", "--model", "gpt-4o", "--json"]
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["model"] == "gpt-4o"
    assert payload["confidence"] == "exact"


def test_tokens_count_json_comparison() -> None:
    result = runner.invoke(app, ["tokens", "count", "hello world", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert isinstance(payload, list)
    assert len(payload) == 6


def test_tokens_unknown_model_exits_1() -> None:
    result = runner.invoke(app, ["tokens", "count", "hi", "--model", "bogus"])
    assert result.exit_code == 1


def test_tokens_unknown_model_json_error() -> None:
    result = runner.invoke(app, ["tokens", "count", "hi", "--model", "bogus", "--json"])
    assert result.exit_code == 1
    payload = json.loads(result.stderr)
    assert "error" in payload and "code" in payload


def test_missing_arg_exits_2() -> None:
    result = runner.invoke(app, ["tokens", "count"])
    assert result.exit_code == 2


def test_cost_estimate_json() -> None:
    result = runner.invoke(
        app,
        [
            "cost",
            "estimate",
            "hello",
            "--model",
            "gpt-4o",
            "--output-tokens",
            "100",
            "--json",
        ],
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["output_tokens"] == 100
    assert payload["total_cost_usd"] > 0


def test_cost_estimate_comparison_table() -> None:
    result = runner.invoke(app, ["cost", "estimate", "hello"])
    assert result.exit_code == 0
    assert "Total $" in result.output


def test_context_plan(tmp_path: Path) -> None:
    file = tmp_path / "doc.txt"
    file.write_text("hello world " * 100, encoding="utf-8")
    result = runner.invoke(app, ["context", "plan", str(file), "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["fits"] is True
    human = runner.invoke(app, ["context", "plan", str(file)])
    assert human.exit_code == 0
    assert "Fits" in human.output


def test_chunk_split(tmp_path: Path) -> None:
    file = tmp_path / "doc.txt"
    file.write_text("hello world. " * 500, encoding="utf-8")
    result = runner.invoke(
        app, ["chunk", "split", str(file), "--max-tokens", "100", "--json"]
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert len(payload) > 1
    human = runner.invoke(app, ["chunk", "split", str(file), "--max-tokens", "100"])
    assert human.exit_code == 0


def test_validate_json_cli(tmp_path: Path) -> None:
    good = tmp_path / "good.json"
    good.write_text('{"a": 1}', encoding="utf-8")
    bad = tmp_path / "bad.json"
    bad.write_text("{nope}", encoding="utf-8")
    assert runner.invoke(app, ["validate", "json", str(good)]).exit_code == 0
    result = runner.invoke(app, ["validate", "json", str(bad), "--json"])
    assert result.exit_code == 1
    assert json.loads(result.stdout)["valid"] is False


def test_validate_json_with_schema_cli(tmp_path: Path) -> None:
    data = tmp_path / "data.json"
    data.write_text('{"a": 1}', encoding="utf-8")
    schema = tmp_path / "schema.json"
    schema.write_text('{"required": ["b"]}', encoding="utf-8")
    result = runner.invoke(
        app, ["validate", "json", str(data), "--schema", str(schema)]
    )
    assert result.exit_code == 1


def test_validate_jsonl_cli(tmp_path: Path) -> None:
    file = tmp_path / "d.jsonl"
    file.write_text('{"a": 1}\n{"b": 2}\n', encoding="utf-8")
    result = runner.invoke(
        app, ["validate", "jsonl", str(file), "--check-keys", "--json"]
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["valid"] is True
    assert payload["warnings"]


def test_validate_csv_cli(tmp_path: Path) -> None:
    file = tmp_path / "d.csv"
    file.write_text("1,2\n3,4\n", encoding="utf-8")
    result = runner.invoke(app, ["validate", "csv", str(file), "--no-header"])
    assert result.exit_code == 0


def test_redact_pii_cli() -> None:
    result = runner.invoke(
        app, ["redact", "pii", "mail bob@example.com", "--patterns", "email", "--json"]
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["redacted_text"] == "mail [EMAIL]"
    human = runner.invoke(app, ["redact", "pii", "mail bob@example.com"])
    assert human.exit_code == 0
    assert "[EMAIL]" in human.output


def test_diff_cli(tmp_path: Path) -> None:
    file_a = tmp_path / "a.txt"
    file_b = tmp_path / "b.txt"
    file_a.write_text("one\ntwo\n", encoding="utf-8")
    file_b.write_text("one\n2\n", encoding="utf-8")
    result = runner.invoke(
        app, ["diff", str(file_a), str(file_b), "--model", "gpt-4o", "--json"]
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["identical"] is False
    assert payload["token_delta"]["model"] == "gpt-4o"
    human = runner.invoke(app, ["diff", str(file_a), str(file_b)])
    assert human.exit_code == 0


def test_diff_identical_files(tmp_path: Path) -> None:
    file_a = tmp_path / "a.txt"
    file_b = tmp_path / "b.txt"
    file_a.write_text("same\n", encoding="utf-8")
    file_b.write_text("same\n", encoding="utf-8")
    result = runner.invoke(app, ["diff", str(file_a), str(file_b)])
    assert result.exit_code == 0
    assert "identical" in result.output.lower()


def test_models_list_and_show() -> None:
    result = runner.invoke(app, ["models", "list", "--json"])
    assert result.exit_code == 0
    assert len(json.loads(result.stdout)) >= 15
    human = runner.invoke(app, ["models", "list"])
    assert human.exit_code == 0
    show = runner.invoke(app, ["models", "show", "claude-sonnet-4", "--json"])
    assert show.exit_code == 0
    assert json.loads(show.stdout)["id"] == "claude-sonnet-4-5"
    show_human = runner.invoke(app, ["models", "show", "gpt-4o"])
    assert show_human.exit_code == 0
    missing = runner.invoke(app, ["models", "show", "bogus"])
    assert missing.exit_code == 1


def test_tools_list() -> None:
    result = runner.invoke(app, ["tools", "list", "--json"])
    assert result.exit_code == 0
    names = {t["name"] for t in json.loads(result.stdout)}
    assert "count_tokens" in names
    human = runner.invoke(app, ["tools", "list"])
    assert human.exit_code == 0


def test_mcp_serve_is_stub() -> None:
    result = runner.invoke(app, ["mcp", "serve"])
    assert result.exit_code == 1
