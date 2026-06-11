"""Bundled model metadata: loading, lookup, and shared types."""

from __future__ import annotations

import json
from functools import lru_cache
from importlib import resources
from typing import Literal

from pydantic import BaseModel, Field

CountingMethod = Literal["tiktoken", "heuristic"]
Confidence = Literal["exact", "estimate"]


class AidexError(Exception):
    """Base class for all aidex domain errors."""


class ModelDataError(AidexError):
    """Raised when the bundled models.json cannot be loaded or parsed."""


class ModelNotFoundError(AidexError):
    """Raised when a model id or alias is not in the bundled catalog."""

    def __init__(self, name: str, known: list[str]) -> None:
        self.name = name
        self.known = known
        super().__init__(
            f"Unknown model {name!r}. Known models: {', '.join(sorted(known))}"
        )


class ModelInfo(BaseModel):
    """Metadata for one model in the bundled catalog."""

    id: str
    aliases: list[str] = Field(default_factory=list)
    context_window: int
    input_price_per_1m: float
    output_price_per_1m: float
    counting_method: CountingMethod
    confidence: Confidence


class ModelCatalog(BaseModel):
    """Parsed contents of models.json."""

    default_comparison_set: list[str]
    models: list[ModelInfo]


@lru_cache(maxsize=1)
def load_catalog() -> ModelCatalog:
    """Load and cache the bundled model catalog."""
    try:
        raw = resources.files("aidex.data").joinpath("models.json").read_text("utf-8")
        return ModelCatalog.model_validate(json.loads(raw))
    except (OSError, ValueError) as exc:
        raise ModelDataError(f"Failed to load bundled models.json: {exc}") from exc


def list_models() -> list[ModelInfo]:
    """Return all models in the bundled catalog."""
    return list(load_catalog().models)


def get_model(name: str) -> ModelInfo:
    """Resolve a model id or alias to its :class:`ModelInfo`.

    Matching is case-insensitive across ids and aliases.
    """
    catalog = load_catalog()
    needle = name.strip().lower()
    for model in catalog.models:
        if model.id.lower() == needle:
            return model
        if any(alias.lower() == needle for alias in model.aliases):
            return model
    raise ModelNotFoundError(name, [m.id for m in catalog.models])


def default_comparison_models() -> list[ModelInfo]:
    """Return the default 6-model comparison set."""
    return [get_model(name) for name in load_catalog().default_comparison_set]
