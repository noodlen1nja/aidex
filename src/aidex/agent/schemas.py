"""JSON Schema definitions for every agent tool."""

from __future__ import annotations

from typing import Any

_MODEL_PROPERTY: dict[str, Any] = {
    "type": ["string", "null"],
    "description": "Model id or alias from the bundled catalog. "
    "Omit or null for the default comparison set.",
}

COUNT_TOKENS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "text": {"type": "string", "description": "Text to count tokens for."},
        "model": _MODEL_PROPERTY,
    },
    "required": ["text"],
    "additionalProperties": False,
}

ESTIMATE_COST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "text": {"type": "string", "description": "Input text to price."},
        "model": _MODEL_PROPERTY,
        "output_tokens": {
            "type": "integer",
            "minimum": 0,
            "default": 0,
            "description": "Expected output tokens to include in the estimate.",
        },
    },
    "required": ["text"],
    "additionalProperties": False,
}

PLAN_CONTEXT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "text": {"type": "string", "description": "Input text to plan."},
        "model": {"type": "string", "default": "gpt-4o"},
        "reserve_output_tokens": {"type": "integer", "minimum": 0, "default": 4096},
        "system_prompt_tokens": {"type": "integer", "minimum": 0, "default": 0},
    },
    "required": ["text"],
    "additionalProperties": False,
}

CHUNK_TEXT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "text": {"type": "string", "description": "Text to split into chunks."},
        "max_tokens": {"type": "integer", "minimum": 1, "default": 512},
        "overlap_tokens": {"type": "integer", "minimum": 0, "default": 50},
        "model": {"type": "string", "default": "gpt-4o"},
        "separators": {
            "type": ["array", "null"],
            "items": {"type": "string"},
            "description": "Separator hierarchy, coarsest first.",
        },
    },
    "required": ["text"],
    "additionalProperties": False,
}

VALIDATE_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "text_or_path": {
            "type": "string",
            "description": "JSON text, or a path to a JSON file.",
        },
        "schema": {
            "type": ["object", "null"],
            "description": "Optional JSON Schema (subset) to validate against.",
        },
    },
    "required": ["text_or_path"],
    "additionalProperties": False,
}

VALIDATE_JSONL_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "path": {"type": "string", "description": "Path to a .jsonl file."},
        "check_keys": {"type": "boolean", "default": False},
    },
    "required": ["path"],
    "additionalProperties": False,
}

VALIDATE_CSV_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "path": {"type": "string", "description": "Path to a .csv file."},
        "has_header": {"type": "boolean", "default": True},
    },
    "required": ["path"],
    "additionalProperties": False,
}

REDACT_PII_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "text": {"type": "string", "description": "Text to redact."},
        "patterns": {
            "type": ["array", "null"],
            "items": {
                "type": "string",
                "enum": ["api_key", "email", "ssn", "credit_card", "ipv4", "phone"],
            },
            "description": "Subset of built-in patterns. Omit for all.",
        },
        "placeholder_style": {
            "type": "string",
            "enum": ["tagged", "generic"],
            "default": "tagged",
        },
    },
    "required": ["text"],
    "additionalProperties": False,
}

DIFF_TEXT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "a": {"type": "string", "description": "First text or file path."},
        "b": {"type": "string", "description": "Second text or file path."},
        "context_lines": {"type": "integer", "minimum": 0, "default": 3},
        "model": _MODEL_PROPERTY,
    },
    "required": ["a", "b"],
    "additionalProperties": False,
}

LIST_MODELS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {},
    "additionalProperties": False,
}
