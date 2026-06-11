"""Recursive token-based text chunking (LangChain-style).

The splitter tries the coarsest separator first ("\\n\\n" by default) and
recurses with progressively finer separators for any piece that still
exceeds ``max_tokens``. When no separator can break a piece down, it is
hard-split at character boundaries chosen so each slice fits the token
budget — this is the documented last resort and can split mid-word.

Overlap is applied by prepending the last ``overlap_tokens`` of the
previous chunk to the next chunk's text. Chunk bodies are budgeted at
``max_tokens - overlap_tokens`` so each chunk (overlap included) stays
within ``max_tokens``. ``start_char``/``end_char`` always describe the
chunk's own (non-overlap) span in the original text.
"""

from __future__ import annotations

import math
from collections.abc import Callable

from pydantic import BaseModel

from aidex.models import AidexError, Confidence, ModelInfo, get_model
from aidex.tokens import CHARS_PER_TOKEN, _encoding_for

DEFAULT_SEPARATORS: list[str] = ["\n\n", "\n", ". ", " "]


class ChunkError(AidexError):
    """Raised for invalid chunking parameters."""


class Chunk(BaseModel):
    """One chunk of text. ``text`` may include an overlap prefix."""

    index: int
    text: str
    token_count: int
    start_char: int
    end_char: int
    confidence: Confidence


def _split_keep_sep(text: str, sep: str) -> list[tuple[int, str]]:
    """Split on ``sep``, keeping the separator attached to the preceding piece
    so offsets and content are preserved exactly."""
    pieces: list[tuple[int, str]] = []
    offset = 0
    while True:
        idx = text.find(sep, offset)
        if idx == -1:
            if offset < len(text):
                pieces.append((offset, text[offset:]))
            return pieces
        end = idx + len(sep)
        pieces.append((offset, text[offset:end]))
        offset = end


def _hard_split(
    text: str, start: int, max_tokens: int, count: Callable[[str], int]
) -> list[tuple[int, str]]:
    pieces: list[tuple[int, str]] = []
    pos = 0
    while pos < len(text):
        take = min(len(text) - pos, max(1, int(max_tokens * CHARS_PER_TOKEN)))
        while take > 1 and count(text[pos : pos + take]) > max_tokens:
            take = max(1, int(take * 0.9))
        pieces.append((start + pos, text[pos : pos + take]))
        pos += take
    return pieces


def _split(
    text: str,
    start: int,
    separators: list[str],
    max_tokens: int,
    count: Callable[[str], int],
) -> list[tuple[int, str]]:
    if not text:
        return []
    if count(text) <= max_tokens:
        return [(start, text)]
    if not separators:
        return _hard_split(text, start, max_tokens, count)
    sep, rest = separators[0], separators[1:]
    parts = _split_keep_sep(text, sep)
    if len(parts) <= 1:
        return _split(text, start, rest, max_tokens, count)
    pieces: list[tuple[int, str]] = []
    for offset, piece in parts:
        if count(piece) <= max_tokens:
            pieces.append((start + offset, piece))
        else:
            pieces.extend(_split(piece, start + offset, rest, max_tokens, count))
    return pieces


def _merge(
    pieces: list[tuple[int, str]], max_tokens: int, count: Callable[[str], int]
) -> list[tuple[int, str]]:
    """Greedily merge adjacent pieces back together up to the token budget."""
    merged: list[tuple[int, str]] = []
    cur_start = 0
    cur_text = ""
    for offset, piece in pieces:
        if cur_text and count(cur_text + piece) <= max_tokens:
            cur_text += piece
        elif not cur_text:
            cur_start, cur_text = offset, piece
        else:
            merged.append((cur_start, cur_text))
            cur_start, cur_text = offset, piece
    if cur_text:
        merged.append((cur_start, cur_text))
    return merged


def _overlap_tail(text: str, overlap_tokens: int, info: ModelInfo) -> str:
    if overlap_tokens <= 0:
        return ""
    if info.counting_method == "tiktoken":
        enc = _encoding_for(info.id)
        ids = enc.encode(text)
        return enc.decode(ids[-overlap_tokens:])
    return text[-int(overlap_tokens * CHARS_PER_TOKEN) :]


def chunk_text(
    text: str,
    max_tokens: int = 512,
    overlap_tokens: int = 50,
    model: str = "gpt-4o",
    separators: list[str] | None = None,
) -> list[Chunk]:
    """Split ``text`` into chunks of at most ``max_tokens`` tokens.

    Token counts use ``model``'s counting method (tiktoken or character
    heuristic) and carry the matching confidence label.
    """
    if max_tokens <= 0:
        raise ChunkError("max_tokens must be > 0")
    if overlap_tokens < 0:
        raise ChunkError("overlap_tokens must be >= 0")
    if overlap_tokens >= max_tokens:
        raise ChunkError("overlap_tokens must be smaller than max_tokens")
    if separators is not None and any(sep == "" for sep in separators):
        # an empty separator would make the splitter loop forever
        raise ChunkError("separators must not contain empty strings")
    if not text:
        return []

    info = get_model(model)

    def count(s: str) -> int:
        if info.counting_method == "tiktoken":
            return len(_encoding_for(info.id).encode(s))
        return math.ceil(len(s) / CHARS_PER_TOKEN)

    body_budget = max_tokens - overlap_tokens
    seps = DEFAULT_SEPARATORS if separators is None else separators
    pieces = _split(text, 0, seps, body_budget, count)
    merged = _merge(pieces, body_budget, count)

    chunks: list[Chunk] = []
    prev_text: str | None = None
    for index, (start, body) in enumerate(merged):
        overlap = _overlap_tail(prev_text, overlap_tokens, info) if prev_text else ""
        full_text = overlap + body
        chunks.append(
            Chunk(
                index=index,
                text=full_text,
                token_count=count(full_text),
                start_char=start,
                end_char=start + len(body),
                confidence=info.confidence,
            )
        )
        prev_text = body
    return chunks
