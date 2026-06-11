"""Token counting for bundled models.

OpenAI models are counted with tiktoken (confidence "exact"). All other
models use a character heuristic (confidence "estimate"): characters
divided by :data:`CHARS_PER_TOKEN`, rounded up. Estimates are never
presented as exact — every result carries its confidence label.

Note: tiktoken downloads encoding files on first use and caches them
locally; afterwards counting is fully offline.
"""

from __future__ import annotations

import math
from functools import lru_cache
from typing import TYPE_CHECKING

from pydantic import BaseModel

from aidex.models import (
    AidexError,
    Confidence,
    CountingMethod,
    ModelInfo,
    default_comparison_models,
    get_model,
)

if TYPE_CHECKING:
    from tiktoken import Encoding

#: Characters per token used by the heuristic counting method. Tunable.
CHARS_PER_TOKEN: float = 4.0

#: Fallback tiktoken encoding for OpenAI models tiktoken does not know by id.
_FALLBACK_ENCODING = "o200k_base"


class TokenCountError(AidexError):
    """Raised when token counting fails (e.g. tiktoken cannot load)."""


class TokenCountResult(BaseModel):
    """Token count for one model, with method and confidence labels."""

    model: str
    token_count: int
    counting_method: CountingMethod
    confidence: Confidence


@lru_cache(maxsize=8)
def _encoding_for(model_id: str) -> Encoding:
    import tiktoken

    try:
        return tiktoken.encoding_for_model(model_id)
    except KeyError:
        return tiktoken.get_encoding(_FALLBACK_ENCODING)


def count_for_model(text: str, info: ModelInfo) -> TokenCountResult:
    """Count tokens for already-resolved model metadata."""
    if info.counting_method == "tiktoken":
        try:
            token_count = len(_encoding_for(info.id).encode(text))
        except Exception as exc:  # tiktoken raises various I/O errors
            raise TokenCountError(
                f"tiktoken failed for model {info.id!r}: {exc}. "
                "tiktoken downloads encoding files on first use; "
                "ensure network access or a populated cache."
            ) from exc
    else:
        token_count = math.ceil(len(text) / CHARS_PER_TOKEN)
    return TokenCountResult(
        model=info.id,
        token_count=token_count,
        counting_method=info.counting_method,
        confidence=info.confidence,
    )


def count_tokens(
    text: str, model: str | None = None
) -> TokenCountResult | list[TokenCountResult]:
    """Count tokens in ``text``.

    With ``model`` set, returns a single :class:`TokenCountResult`.
    With ``model=None``, returns results for the default comparison set.
    """
    if model is not None:
        return count_for_model(text, get_model(model))
    return [count_for_model(text, info) for info in default_comparison_models()]
