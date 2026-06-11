import pytest

from aidex.cost import CostEstimateError, CostResult, estimate_cost
from aidex.models import get_model
from aidex.tokens import count_tokens


def test_cost_formula_single_model() -> None:
    text = "hello world " * 50
    result = estimate_cost(text, model="gpt-4o", output_tokens=1000)
    assert isinstance(result, CostResult)
    info = get_model("gpt-4o")
    tokens = count_tokens(text, model="gpt-4o")
    assert not isinstance(tokens, list)
    expected_input = tokens.token_count * info.input_price_per_1m / 1_000_000
    expected_output = 1000 * info.output_price_per_1m / 1_000_000
    assert result.input_tokens == tokens.token_count
    assert result.output_tokens == 1000
    assert result.input_cost_usd == pytest.approx(expected_input)
    assert result.output_cost_usd == pytest.approx(expected_output)
    assert result.total_cost_usd == pytest.approx(expected_input + expected_output)
    assert result.confidence == "exact"


def test_zero_output_tokens_costs_nothing_on_output() -> None:
    result = estimate_cost("hi", model="claude-haiku-4-5")
    assert isinstance(result, CostResult)
    assert result.output_tokens == 0
    assert result.output_cost_usd == 0.0
    assert result.confidence == "estimate"


def test_default_comparison_returns_six() -> None:
    results = estimate_cost("hello", output_tokens=10)
    assert isinstance(results, list)
    assert len(results) == 6
    for r in results:
        assert r.total_cost_usd >= 0


def test_negative_output_tokens_raises() -> None:
    with pytest.raises(CostEstimateError):
        estimate_cost("hello", model="gpt-4o", output_tokens=-1)
