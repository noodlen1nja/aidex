import math

import pytest

from aidex.models import ModelNotFoundError, get_model, list_models
from aidex.tokens import CHARS_PER_TOKEN, TokenCountResult, count_tokens


def test_single_model_exact() -> None:
    result = count_tokens("hello world", model="gpt-4o")
    assert isinstance(result, TokenCountResult)
    assert result.model == "gpt-4o"
    assert result.token_count > 0
    assert result.counting_method == "tiktoken"
    assert result.confidence == "exact"


def test_heuristic_count_is_chars_over_four() -> None:
    text = "x" * 100
    result = count_tokens(text, model="claude-sonnet-4-5")
    assert isinstance(result, TokenCountResult)
    assert result.token_count == math.ceil(100 / CHARS_PER_TOKEN)
    assert result.counting_method == "heuristic"
    assert result.confidence == "estimate"


def test_empty_text_counts_zero_heuristic() -> None:
    result = count_tokens("", model="claude-haiku-4-5")
    assert isinstance(result, TokenCountResult)
    assert result.token_count == 0


def test_default_comparison_set_has_six_models() -> None:
    results = count_tokens("hello world")
    assert isinstance(results, list)
    assert len(results) == 6
    assert {r.model for r in results} == {
        "gpt-5.5",
        "gpt-5.4-mini",
        "claude-sonnet-4-6",
        "claude-haiku-4-5",
        "gemini-3.1-pro",
        "gemini-3.5-flash",
    }
    for r in results:
        assert r.confidence in ("exact", "estimate")


def test_unknown_model_raises() -> None:
    with pytest.raises(ModelNotFoundError):
        count_tokens("hello", model="not-a-model")


def test_alias_resolution() -> None:
    assert get_model("claude-sonnet").id == "claude-sonnet-4-6"
    assert get_model("claude-haiku").id == "claude-haiku-4-5"
    assert get_model("gemini-pro").id == "gemini-3.1-pro"
    assert get_model("deepseek-chat").id == "deepseek-v4-flash"


def test_model_lookup_is_case_insensitive() -> None:
    assert get_model("GPT-4o").id == "gpt-4o"


def test_catalog_has_at_least_fifteen_models() -> None:
    assert len(list_models()) >= 15


def test_estimates_never_labeled_exact() -> None:
    for model in list_models():
        if model.counting_method == "heuristic":
            assert model.confidence == "estimate"
        else:
            assert model.confidence == "exact"
