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

#: Default characters per token for the heuristic counter, used when a model
#: declares no ``chars_per_token`` and matches no known provider.
CHARS_PER_TOKEN: float = 4.0

#: Provider-inferred chars-per-token fallbacks, keyed by model-id prefix and
#: tried in order. These are rough averages for English prose: Claude's
#: tokenizer runs denser than GPT's (more tokens, fewer chars each), so its
#: divisor is lower. Counts stay labeled "estimate" regardless.
_PROVIDER_CHARS_PER_TOKEN: tuple[tuple[str, float], ...] = (
    ("claude", 3.5),
    ("gemini", 4.0),
    ("deepseek", 3.5),
    ("mistral", 3.8),
    ("llama", 3.8),
)

#: Fallback tiktoken encoding for OpenAI models tiktoken does not know by id.
_FALLBACK_ENCODING = "o200k_base"


def chars_per_token(info: ModelInfo) -> float:
    """Effective characters-per-token divisor for ``info``'s heuristic count.

    Resolution order: the model's explicit ``chars_per_token`` if set, then a
    provider default inferred from the model id, then :data:`CHARS_PER_TOKEN`.
    """
    if info.chars_per_token is not None:
        return info.chars_per_token
    needle = info.id.lower()
    for prefix, value in _PROVIDER_CHARS_PER_TOKEN:
        if needle.startswith(prefix):
            return value
    return CHARS_PER_TOKEN


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
        token_count = math.ceil(len(text) / chars_per_token(info))
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
