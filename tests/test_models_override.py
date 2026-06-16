import json
from collections.abc import Iterator
from pathlib import Path

import pytest

from aidex.models import (
    ENV_MODELS_FILE,
    ModelDataError,
    default_comparison_models,
    get_model,
    list_models,
    load_catalog,
)


@pytest.fixture(autouse=True)
def _clear_catalog_cache() -> Iterator[None]:
    # the catalog is process-cached; isolate each test from the others
    load_catalog.cache_clear()
    yield
    load_catalog.cache_clear()


def _write(path: Path, payload: dict[str, object]) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_no_env_returns_bundled() -> None:
    # gpt-4o is a bundled model with known pricing
    assert get_model("gpt-4o").input_price_per_1m == 2.5


def test_override_existing_price(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    override = _write(
        tmp_path / "models.json",
        {
            "models": [
                {
                    "id": "gpt-4o",
                    "aliases": ["4o"],
                    "context_window": 128000,
                    "input_price_per_1m": 99.0,
                    "output_price_per_1m": 199.0,
                    "counting_method": "tiktoken",
                    "confidence": "exact",
                }
            ]
        },
    )
    monkeypatch.setenv(ENV_MODELS_FILE, str(override))
    load_catalog.cache_clear()
    model = get_model("gpt-4o")
    assert model.input_price_per_1m == 99.0
    assert model.output_price_per_1m == 199.0
    # untouched bundled models still resolve
    assert get_model("gpt-5.5").input_price_per_1m == 5.0


def test_add_new_model(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    override = _write(
        tmp_path / "models.json",
        {
            "models": [
                {
                    "id": "my-internal-llm",
                    "aliases": ["internal"],
                    "context_window": 32000,
                    "input_price_per_1m": 0.0,
                    "output_price_per_1m": 0.0,
                    "counting_method": "heuristic",
                    "confidence": "estimate",
                }
            ]
        },
    )
    monkeypatch.setenv(ENV_MODELS_FILE, str(override))
    load_catalog.cache_clear()
    assert get_model("internal").id == "my-internal-llm"
    ids = {m.id for m in list_models()}
    assert "my-internal-llm" in ids
    assert "gpt-4o" in ids  # bundled models are preserved


def test_override_default_comparison_set(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    override = _write(
        tmp_path / "models.json",
        {"default_comparison_set": ["gpt-4o", "gpt-4o-mini"]},
    )
    monkeypatch.setenv(ENV_MODELS_FILE, str(override))
    load_catalog.cache_clear()
    assert [m.id for m in default_comparison_models()] == ["gpt-4o", "gpt-4o-mini"]


def test_empty_comparison_set_falls_back_to_bundled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    override = _write(tmp_path / "models.json", {"default_comparison_set": []})
    monkeypatch.setenv(ENV_MODELS_FILE, str(override))
    load_catalog.cache_clear()
    assert len(default_comparison_models()) == 6


def test_bad_override_file_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bad = tmp_path / "models.json"
    bad.write_text("not json", encoding="utf-8")
    monkeypatch.setenv(ENV_MODELS_FILE, str(bad))
    load_catalog.cache_clear()
    with pytest.raises(ModelDataError):
        list_models()


def test_missing_override_file_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_MODELS_FILE, "/nonexistent/models.json")
    load_catalog.cache_clear()
    with pytest.raises(ModelDataError):
        list_models()
