"""Context window planning: will this text fit, and if not, how to chunk it."""

from __future__ import annotations

import math

from pydantic import BaseModel

from aidex.models import AidexError, Confidence, get_model
from aidex.tokens import count_for_model

#: Safety margin (fraction of the context window) applied to chunk suggestions.
_SAFETY_MARGIN = 0.05


class ContextPlanError(AidexError):
    """Raised when a context plan cannot be computed."""


class ChunkSuggestion(BaseModel):
    """Suggested chunking strategy when the input does not fit."""

    action: str = "chunk"
    target_chunk_tokens: int
    estimated_chunks: int


class ContextPlan(BaseModel):
    """Result of planning ``text`` against a model's context window."""

    model: str
    context_window: int
    input_tokens: int
    reserved_output: int
    system_overhead: int
    total_required: int
    fits: bool
    headroom: int
    utilization_pct: float
    confidence: Confidence
    suggestion: ChunkSuggestion | None = None


def plan_context(
    text: str,
    model: str = "gpt-4o",
    reserve_output_tokens: int = 4096,
    system_prompt_tokens: int = 0,
) -> ContextPlan:
    """Check whether ``text`` fits in ``model``'s context window.

    Accounts for reserved output tokens and system prompt overhead. When the
    total does not fit, a chunking suggestion (with a 5% safety margin) is
    included.
    """
    if reserve_output_tokens < 0 or system_prompt_tokens < 0:
        raise ContextPlanError(
            "reserve_output_tokens and system_prompt_tokens must be >= 0"
        )
    info = get_model(model)
    result = count_for_model(text, info)
    input_tokens = result.token_count
    total_required = input_tokens + reserve_output_tokens + system_prompt_tokens
    fits = total_required <= info.context_window
    headroom = info.context_window - total_required
    utilization_pct = round(total_required / info.context_window * 100, 2)

    suggestion: ChunkSuggestion | None = None
    if not fits:
        target = (
            info.context_window
            - reserve_output_tokens
            - system_prompt_tokens
            - int(info.context_window * _SAFETY_MARGIN)
        )
        if target <= 0:
            raise ContextPlanError(
                f"Reserved output ({reserve_output_tokens}) plus system overhead "
                f"({system_prompt_tokens}) leaves no room for input in "
                f"{info.id}'s {info.context_window}-token context window."
            )
        suggestion = ChunkSuggestion(
            target_chunk_tokens=target,
            estimated_chunks=math.ceil(input_tokens / target),
        )

    return ContextPlan(
        model=info.id,
        context_window=info.context_window,
        input_tokens=input_tokens,
        reserved_output=reserve_output_tokens,
        system_overhead=system_prompt_tokens,
        total_required=total_required,
        fits=fits,
        headroom=headroom,
        utilization_pct=utilization_pct,
        confidence=info.confidence,
        suggestion=suggestion,
    )
