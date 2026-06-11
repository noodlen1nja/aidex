"""Agent tool registry.

All tools auto-register from the single :data:`TOOLS` list. Arguments are
validated with Pydantic before dispatch, and every result is a
JSON-serializable dict built from the library's Pydantic models.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from pydantic import ValidationError as PydanticValidationError

from aidex.chunk import chunk_text
from aidex.context import plan_context
from aidex.cost import estimate_cost
from aidex.diff import diff_text
from aidex.models import AidexError, list_models
from aidex.redact import redact_pii
from aidex.tokens import count_tokens
from aidex.validate import validate_csv, validate_json, validate_jsonl

from . import schemas


class ToolNotFoundError(AidexError):
    """Raised when call_tool is given an unknown tool name."""

    def __init__(self, name: str, known: list[str]) -> None:
        super().__init__(f"Unknown tool {name!r}. Available tools: {', '.join(known)}")


class ToolArgumentError(AidexError):
    """Raised when call_tool arguments fail validation."""


class _StrictArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")


class _CountTokensArgs(_StrictArgs):
    text: str
    model: str | None = None


class _EstimateCostArgs(_StrictArgs):
    text: str
    model: str | None = None
    output_tokens: int = Field(default=0, ge=0)


class _PlanContextArgs(_StrictArgs):
    text: str
    model: str = "gpt-4o"
    reserve_output_tokens: int = Field(default=4096, ge=0)
    system_prompt_tokens: int = Field(default=0, ge=0)


class _ChunkTextArgs(_StrictArgs):
    text: str
    max_tokens: int = Field(default=512, ge=1)
    overlap_tokens: int = Field(default=50, ge=0)
    model: str = "gpt-4o"
    separators: list[str] | None = None


class _ValidateJsonArgs(_StrictArgs):
    text_or_path: str
    schema_: dict[str, Any] | None = Field(default=None, alias="schema")

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class _ValidateJsonlArgs(_StrictArgs):
    path: str
    check_keys: bool = False


class _ValidateCsvArgs(_StrictArgs):
    path: str
    has_header: bool = True


class _RedactPiiArgs(_StrictArgs):
    text: str
    patterns: list[str] | None = None
    placeholder_style: str = "tagged"


class _DiffTextArgs(_StrictArgs):
    a: str
    b: str
    context_lines: int = Field(default=3, ge=0)
    model: str | None = None


class _NoArgs(_StrictArgs):
    pass


def _dump(result: BaseModel | Sequence[BaseModel]) -> dict[str, Any]:
    if isinstance(result, BaseModel):
        return result.model_dump()
    return {"results": [item.model_dump() for item in result]}


def _count_tokens_handler(args: _CountTokensArgs) -> dict[str, Any]:
    return _dump(count_tokens(args.text, args.model))


def _estimate_cost_handler(args: _EstimateCostArgs) -> dict[str, Any]:
    return _dump(estimate_cost(args.text, args.model, args.output_tokens))


def _plan_context_handler(args: _PlanContextArgs) -> dict[str, Any]:
    return _dump(
        plan_context(
            args.text,
            model=args.model,
            reserve_output_tokens=args.reserve_output_tokens,
            system_prompt_tokens=args.system_prompt_tokens,
        )
    )


def _chunk_text_handler(args: _ChunkTextArgs) -> dict[str, Any]:
    chunks = chunk_text(
        args.text,
        max_tokens=args.max_tokens,
        overlap_tokens=args.overlap_tokens,
        model=args.model,
        separators=args.separators,
    )
    return {"chunks": [chunk.model_dump() for chunk in chunks]}


def _validate_json_handler(args: _ValidateJsonArgs) -> dict[str, Any]:
    return _dump(validate_json(args.text_or_path, schema=args.schema_))


def _validate_jsonl_handler(args: _ValidateJsonlArgs) -> dict[str, Any]:
    return _dump(validate_jsonl(args.path, check_keys=args.check_keys))


def _validate_csv_handler(args: _ValidateCsvArgs) -> dict[str, Any]:
    return _dump(validate_csv(args.path, has_header=args.has_header))


def _redact_pii_handler(args: _RedactPiiArgs) -> dict[str, Any]:
    return _dump(
        redact_pii(
            args.text,
            patterns=args.patterns,
            placeholder_style=args.placeholder_style,
        )
    )


def _diff_text_handler(args: _DiffTextArgs) -> dict[str, Any]:
    return _dump(
        diff_text(args.a, args.b, context_lines=args.context_lines, model=args.model)
    )


def _list_models_handler(_args: _NoArgs) -> dict[str, Any]:
    return {"models": [model.model_dump() for model in list_models()]}


@dataclass(frozen=True)
class ToolSpec:
    """One registered tool: schema for discovery, Pydantic model for
    validation, and a handler that returns a JSON-serializable dict."""

    name: str
    description: str
    input_schema: dict[str, Any]
    args_model: type[BaseModel]
    handler: Callable[[Any], dict[str, Any]]


TOOLS: list[ToolSpec] = [
    ToolSpec(
        name="count_tokens",
        description="Count tokens in text for one model, or compare across the "
        "default model set. Results carry counting method and confidence.",
        input_schema=schemas.COUNT_TOKENS_SCHEMA,
        args_model=_CountTokensArgs,
        handler=_count_tokens_handler,
    ),
    ToolSpec(
        name="estimate_cost",
        description="Estimate USD cost for input text plus expected output "
        "tokens, using bundled per-model pricing.",
        input_schema=schemas.ESTIMATE_COST_SCHEMA,
        args_model=_EstimateCostArgs,
        handler=_estimate_cost_handler,
    ),
    ToolSpec(
        name="plan_context",
        description="Check whether text fits a model's context window given "
        "reserved output and system prompt overhead; suggests chunking if not.",
        input_schema=schemas.PLAN_CONTEXT_SCHEMA,
        args_model=_PlanContextArgs,
        handler=_plan_context_handler,
    ),
    ToolSpec(
        name="chunk_text",
        description="Split text into token-bounded chunks with configurable "
        "overlap using recursive separator-aware splitting.",
        input_schema=schemas.CHUNK_TEXT_SCHEMA,
        args_model=_ChunkTextArgs,
        handler=_chunk_text_handler,
    ),
    ToolSpec(
        name="validate_json",
        description="Validate JSON text or a JSON file (strict syntax), "
        "optionally against a JSON Schema subset.",
        input_schema=schemas.VALIDATE_JSON_SCHEMA,
        args_model=_ValidateJsonArgs,
        handler=_validate_json_handler,
    ),
    ToolSpec(
        name="validate_jsonl",
        description="Validate a JSONL file: every non-empty line must be valid "
        "JSON. Optionally warn when keys differ across lines.",
        input_schema=schemas.VALIDATE_JSONL_SCHEMA,
        args_model=_ValidateJsonlArgs,
        handler=_validate_jsonl_handler,
    ),
    ToolSpec(
        name="validate_csv",
        description="Validate a CSV file: parseable with a consistent column "
        "count per row.",
        input_schema=schemas.VALIDATE_CSV_SCHEMA,
        args_model=_ValidateCsvArgs,
        handler=_validate_csv_handler,
    ),
    ToolSpec(
        name="redact_pii",
        description="Redact emails, phones, SSNs, credit cards, IPv4 addresses "
        "and API keys from text using regex patterns. One-way; audit trail "
        "never contains original values.",
        input_schema=schemas.REDACT_PII_SCHEMA,
        args_model=_RedactPiiArgs,
        handler=_redact_pii_handler,
    ),
    ToolSpec(
        name="diff_text",
        description="Unified diff between two texts or files, with line stats "
        "and an optional per-model token delta.",
        input_schema=schemas.DIFF_TEXT_SCHEMA,
        args_model=_DiffTextArgs,
        handler=_diff_text_handler,
    ),
    ToolSpec(
        name="list_models",
        description="List the bundled model catalog with context windows, "
        "pricing, counting method, and confidence.",
        input_schema=schemas.LIST_MODELS_SCHEMA,
        args_model=_NoArgs,
        handler=_list_models_handler,
    ),
]


def list_tools() -> list[dict[str, Any]]:
    """Return name, description, and input schema for every registered tool."""
    return [
        {
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.input_schema,
        }
        for tool in TOOLS
    ]


def call_tool(name: str, args: dict[str, Any]) -> dict[str, Any]:
    """Validate ``args`` for tool ``name``, run it, and return a JSON dict."""
    for tool in TOOLS:
        if tool.name == name:
            try:
                validated = tool.args_model.model_validate(args)
            except PydanticValidationError as exc:
                raise ToolArgumentError(
                    f"Invalid arguments for tool {name!r}: {exc}"
                ) from exc
            return tool.handler(validated)
    raise ToolNotFoundError(name, [tool.name for tool in TOOLS])
