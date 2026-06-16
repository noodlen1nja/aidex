import math

import pytest

from aidex.models import ModelInfo, ModelNotFoundError, get_model, list_models
from aidex.tokens import (
    CHARS_PER_TOKEN,
    TokenCountResult,
    chars_per_token,
    count_tokens,
)


def test_single_model_exact() -> None:
    result = count_tokens("hello world", model="gpt-4o")
    assert isinstance(result, TokenCountResult)
    assert result.model == "gpt-4o"
    assert result.token_count > 0
    assert result.counting_method == "tiktoken"
    assert result.confidence == "exact"


def test_heuristic_count_uses_effective_divisor() -> None:
    text = "x" * 100
    info = get_model("claude-sonnet-4-6")
    result = count_tokens(text, model="claude-sonnet-4-6")
    assert isinstance(result, TokenCountResult)
    assert result.token_count == math.ceil(100 / chars_per_token(info))
    assert result.counting_method == "heuristic"
    assert result.confidence == "estimate"


def _info(model_id: str, cpt: float | None = None) -> ModelInfo:
    return ModelInfo(
        id=model_id,
        context_window=1000,
        input_price_per_1m=1.0,
        output_price_per_1m=1.0,
        counting_method="heuristic",
        confidence="estimate",
        chars_per_token=cpt,
    )


def test_explicit_chars_per_token_wins() -> None:
    assert chars_per_token(_info("claude-sonnet-4-6", cpt=4.2)) == 4.2


def test_provider_inferred_chars_per_token() -> None:
    # Claude runs denser than GPT, so its inferred divisor is below 4.0
    assert chars_per_token(_info("claude-sonnet-4-6")) == 3.5
    assert chars_per_token(_info("gemini-3.1-pro")) == 4.0


def test_unknown_provider_falls_back_to_default() -> None:
    assert chars_per_token(_info("some-private-model")) == CHARS_PER_TOKEN


def test_denser_tokenizer_yields_more_tokens() -> None:
    text = "The quick brown fox jumps over the lazy dog. " * 20
    claude = count_tokens(text, model="claude-sonnet-4-6")
    gemini = count_tokens(text, model="gemini-3.1-pro")
    assert isinstance(claude, TokenCountResult)
    assert isinstance(gemini, TokenCountResult)
    # same text, lower divisor for Claude -> strictly more estimated tokens
    assert claude.token_count > gemini.token_count


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
