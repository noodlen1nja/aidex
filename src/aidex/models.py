"""Bundled model metadata: loading, lookup, and shared types."""

from __future__ import annotations

import json
import os
from functools import lru_cache
from importlib import resources
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

CountingMethod = Literal["tiktoken", "heuristic"]
Confidence = Literal["exact", "estimate"]

#: Env var pointing at an external models.json that overrides bundled pricing.
ENV_MODELS_FILE = "AIDEX_MODELS_FILE"


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
    #: Characters per token for the heuristic counter. Optional; when omitted,
    #: a provider-inferred default is used (see aidex.tokens). Ignored for
    #: tiktoken-counted models.
    chars_per_token: float | None = Field(default=None, gt=0)


class ModelCatalog(BaseModel):
    """Parsed contents of models.json."""

    default_comparison_set: list[str]
    models: list[ModelInfo]


class ModelCatalogOverlay(BaseModel):
    """An external models file merged over the bundled catalog.

    Both fields are optional, so a file may override just a price, just the
    default comparison set, or add new models.
    """

    default_comparison_set: list[str] | None = None
    models: list[ModelInfo] = Field(default_factory=list)


def _load_bundled() -> ModelCatalog:
    try:
        raw = resources.files("aidex.data").joinpath("models.json").read_text("utf-8")
        return ModelCatalog.model_validate(json.loads(raw))
    except (OSError, ValueError) as exc:
        raise ModelDataError(f"Failed to load bundled models.json: {exc}") from exc


def _load_overlay(path: Path) -> ModelCatalogOverlay:
    try:
        raw = path.read_text("utf-8")
        return ModelCatalogOverlay.model_validate(json.loads(raw))
    except (OSError, ValueError) as exc:
        raise ModelDataError(
            f"Failed to load models file {str(path)!r} "
            f"(from ${ENV_MODELS_FILE}): {exc}"
        ) from exc


def _merge(base: ModelCatalog, overlay: ModelCatalogOverlay) -> ModelCatalog:
    # dict preserves order: bundled models keep position, overrides replace
    # in place by id, brand-new ids are appended.
    by_id: dict[str, ModelInfo] = {model.id: model for model in base.models}
    for model in overlay.models:
        by_id[model.id] = model
    comparison = overlay.default_comparison_set or base.default_comparison_set
    return ModelCatalog(default_comparison_set=comparison, models=list(by_id.values()))


@lru_cache(maxsize=1)
def load_catalog() -> ModelCatalog:
    """Load and cache the model catalog.

    Returns the bundled catalog by default. If the ``AIDEX_MODELS_FILE``
    environment variable points to a JSON file, its entries are merged over
    the bundle: a model whose ``id`` matches a bundled one overrides that
    entry (full replacement), new ids are added, and an optional
    ``default_comparison_set`` overrides the default. This lets callers
    correct stale prices or add private models without a new release.

    The result is cached. After changing the environment variable or the
    file within a running process, call ``load_catalog.cache_clear()``.
    """
    base = _load_bundled()
    override = os.environ.get(ENV_MODELS_FILE)
    if not override:
        return base
    return _merge(base, _load_overlay(Path(override)))


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
