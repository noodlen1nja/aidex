import pytest

from aidex.chunk import ChunkError, chunk_text

SAMPLE = "\n\n".join(
    f"Paragraph {i}. " + "Lorem ipsum dolor sit amet, consectetur. " * 8
    for i in range(12)
)


def test_chunks_respect_max_tokens() -> None:
    chunks = chunk_text(SAMPLE, max_tokens=100, overlap_tokens=0, model="gpt-4o")
    assert len(chunks) > 1
    for chunk in chunks:
        assert chunk.token_count <= 100
        assert chunk.confidence == "exact"


def test_spans_reconstruct_original_text() -> None:
    chunks = chunk_text(SAMPLE, max_tokens=100, overlap_tokens=0, model="gpt-4o")
    rebuilt = "".join(SAMPLE[c.start_char : c.end_char] for c in chunks)
    assert rebuilt == SAMPLE
    for chunk in chunks:
        assert chunk.text == SAMPLE[chunk.start_char : chunk.end_char]


def test_overlap_prepends_previous_tail() -> None:
    chunks = chunk_text(SAMPLE, max_tokens=100, overlap_tokens=20, model="gpt-4o")
    assert len(chunks) > 1
    second = chunks[1]
    body = SAMPLE[second.start_char : second.end_char]
    assert second.text.endswith(body)
    assert len(second.text) > len(body)  # overlap prefix present
    prefix = second.text[: len(second.text) - len(body)]
    assert chunks[0].text.endswith(prefix)


def test_heuristic_model_chunks() -> None:
    chunks = chunk_text(SAMPLE, max_tokens=80, model="claude-sonnet-4-5")
    assert chunks
    for chunk in chunks:
        assert chunk.token_count <= 80
        assert chunk.confidence == "estimate"


def test_hard_split_without_separators() -> None:
    text = "x" * 2000  # no separators at all
    chunks = chunk_text(text, max_tokens=50, overlap_tokens=0, model="gpt-4o")
    assert len(chunks) > 1
    for chunk in chunks:
        assert chunk.token_count <= 50
    rebuilt = "".join(text[c.start_char : c.end_char] for c in chunks)
    assert rebuilt == text


def test_empty_text_returns_no_chunks() -> None:
    assert chunk_text("") == []


def test_short_text_single_chunk() -> None:
    chunks = chunk_text("hello world", max_tokens=512)
    assert len(chunks) == 1
    assert chunks[0].index == 0
    assert chunks[0].start_char == 0
    assert chunks[0].end_char == len("hello world")


@pytest.mark.parametrize(
    ("max_tokens", "overlap"),
    [(0, 0), (-5, 0), (10, -1), (10, 10), (10, 20)],
)
def test_invalid_params_raise(max_tokens: int, overlap: int) -> None:
    with pytest.raises(ChunkError):
        chunk_text("hello", max_tokens=max_tokens, overlap_tokens=overlap)


def test_custom_separators() -> None:
    text = "alpha|beta|gamma|delta" * 20
    chunks = chunk_text(text, max_tokens=20, overlap_tokens=0, separators=["|"])
    assert len(chunks) > 1
    rebuilt = "".join(text[c.start_char : c.end_char] for c in chunks)
    assert rebuilt == text
