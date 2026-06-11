"""Cost estimation based on bundled per-model pricing."""

from __future__ import annotations

from pydantic import BaseModel

from aidex.models import (
    AidexError,
    Confidence,
    ModelInfo,
    default_comparison_models,
    get_model,
)
from aidex.tokens import count_for_model


class CostEstimateError(AidexError):
    """Raised when a cost estimate cannot be computed."""


class CostResult(BaseModel):
    """Estimated cost for one model."""

    model: str
    input_tokens: int
    output_tokens: int
    input_cost_usd: float
    output_cost_usd: float
    total_cost_usd: float
    confidence: Confidence


def _estimate_for_model(text: str, info: ModelInfo, output_tokens: int) -> CostResult:
    input_tokens = count_for_model(text, info).token_count
    input_cost = input_tokens * info.input_price_per_1m / 1_000_000
    output_cost = output_tokens * info.output_price_per_1m / 1_000_000
    return CostResult(
        model=info.id,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        input_cost_usd=input_cost,
        output_cost_usd=output_cost,
        total_cost_usd=input_cost + output_cost,
        confidence=info.confidence,
    )


def estimate_cost(
    text: str, model: str | None = None, output_tokens: int = 0
) -> CostResult | list[CostResult]:
    """Estimate USD cost of sending ``text`` plus ``output_tokens`` of output.

    With ``model`` set, returns a single :class:`CostResult`. With
    ``model=None``, returns a comparison across the default model set.
    """
    if output_tokens < 0:
        raise CostEstimateError("output_tokens must be >= 0")
    if model is not None:
        return _estimate_for_model(text, get_model(model), output_tokens)
    return [
        _estimate_for_model(text, info, output_tokens)
        for info in default_comparison_models()
    ]
