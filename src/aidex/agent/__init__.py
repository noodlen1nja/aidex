"""Agent tool surface: JSON Schema discovery and dispatch."""

from aidex.agent.registry import (
    TOOLS,
    ToolArgumentError,
    ToolNotFoundError,
    ToolSpec,
    call_tool,
    list_tools,
)

__all__ = [
    "TOOLS",
    "ToolArgumentError",
    "ToolNotFoundError",
    "ToolSpec",
    "call_tool",
    "list_tools",
]
