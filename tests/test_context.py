import math

import pytest

from aidex.context import ContextPlanError, plan_context


def test_small_text_fits() -> None:
    plan = plan_context("hello world", model="gpt-4o")
    assert plan.fits is True
    assert plan.suggestion is None
    assert plan.headroom > 0
    assert plan.model == "gpt-4o"
    assert plan.context_window == 128000
    assert plan.total_required == plan.input_tokens + 4096
    assert 0 < plan.utilization_pct < 100


def test_oversized_text_gets_chunk_suggestion() -> None:
    # claude-haiku-4-5: 200k window, heuristic => 1.2M chars ≈ 300k tokens
    text = "a" * 1_200_000
    plan = plan_context(text, model="claude-haiku-4-5", reserve_output_tokens=4096)
    assert plan.fits is False
    assert plan.headroom < 0
    assert plan.utilization_pct > 100
    assert plan.suggestion is not None
    assert plan.suggestion.action == "chunk"
    expected_target = 200000 - 4096 - int(200000 * 0.05)
    assert plan.suggestion.target_chunk_tokens == expected_target
    assert plan.suggestion.estimated_chunks == math.ceil(
        plan.input_tokens / expected_target
    )


def test_system_prompt_tokens_counted() -> None:
    plan = plan_context("hi", model="gpt-4o", system_prompt_tokens=500)
    assert plan.system_overhead == 500
    assert plan.total_required == plan.input_tokens + 4096 + 500


def test_negative_reserve_raises() -> None:
    with pytest.raises(ContextPlanError):
        plan_context("hi", reserve_output_tokens=-1)


def test_reserve_exceeding_window_raises_when_not_fitting() -> None:
    with pytest.raises(ContextPlanError):
        plan_context(
            "a" * 4000, model="claude-haiku-4-5", reserve_output_tokens=200_000
        )


def test_confidence_propagates() -> None:
    assert plan_context("hi", model="gpt-4o").confidence == "exact"
    assert plan_context("hi", model="gemini-2.5-pro").confidence == "estimate"
