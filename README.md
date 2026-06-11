# Aidex

Offline AI developer tooling: token counting, cost estimation, context window
planning, text chunking, data validation, PII redaction, and diffing — as a
Python library, a CLI, and an agent tool surface.

No API keys. No network calls in core tool functions.

> **Note on tiktoken:** OpenAI token counting uses
> [tiktoken](https://github.com/openai/tiktoken), which downloads its encoding
> files once on first use and caches them locally. After that first run,
> everything is fully offline.

## Install

```bash
pip install aidex
# or
uv add aidex
```

Requires Python >= 3.11.

## Quickstart (library)

```python
from aidex.tokens import count_tokens
from aidex.cost import estimate_cost
from aidex.context import plan_context
from aidex.chunk import chunk_text
from aidex.redact import redact_pii
from aidex.diff import diff_text
from aidex.validate.json import validate_json
from aidex.validate.jsonl import validate_jsonl
from aidex.validate.csv_module import validate_csv

# Count tokens for one model...
result = count_tokens("hello world", model="gpt-4o")
print(result.token_count, result.confidence)  # 2 exact

# ...or compare across the default 6-model set
for r in count_tokens("hello world"):
    print(r.model, r.token_count, r.confidence)

# Estimate cost
cost = estimate_cost("some prompt", model="claude-sonnet-4-5", output_tokens=500)
print(f"${cost.total_cost_usd:.6f} ({cost.confidence})")

# Will it fit?
plan = plan_context(open("big_doc.txt").read(), model="gpt-4o")
if not plan.fits and plan.suggestion:
    print(f"Chunk into ~{plan.suggestion.estimated_chunks} pieces")

# Chunk it
chunks = chunk_text(open("big_doc.txt").read(), max_tokens=512, overlap_tokens=50)

# Redact PII (one-way; audit trail never contains original values)
redacted = redact_pii("Contact bob@example.com or 555-867-5309")
print(redacted.redacted_text)  # Contact [EMAIL] or [PHONE]
```

Every public function returns a Pydantic model that serializes cleanly to
JSON — the same shapes the CLI emits with `--json` and the agent registry
returns from `call_tool`.

## Confidence labeling (honesty is mandatory)

Token counts are only exact when the tokenizer is public. Aidex never
presents an estimate as exact:

| Provider | Counting method | Confidence |
| --- | --- | --- |
| OpenAI (gpt-4o, gpt-4.1, o3, …) | tiktoken | `exact` |
| Anthropic, Google, others | character heuristic (chars ÷ 4) | `estimate` |

Every result — token counts, costs, context plans, chunks, token deltas —
carries a `confidence` field, and CLI comparison tables show a Confidence
column.

## CLI

Every subcommand supports `--json` for machine-readable output. Exit codes:
`0` success, `1` runtime/validation error, `2` usage error. Errors go to
stderr (as `{"error": "...", "code": "..."}` in `--json` mode).

```bash
aidex tokens count "How many tokens is this?"        # compare 6 models
aidex tokens count prompt.txt --model gpt-4o --json

aidex cost estimate prompt.txt --model claude-sonnet-4-5 --output-tokens 1000

aidex context plan big_doc.txt --model gpt-4o --reserve-output 4096

aidex chunk split big_doc.txt --max-tokens 512 --overlap 50

aidex validate json config.json --schema schema.json
aidex validate jsonl dataset.jsonl --check-keys
aidex validate csv data.csv --no-header

aidex redact pii "email bob@example.com, key sk-abc123def456ghi789" \
    --patterns email,api_key

aidex diff old_prompt.txt new_prompt.txt --model gpt-4o

aidex models list
aidex models show claude-sonnet-4-5
aidex tools list
```

## Agent registry

All tools are exposed through a single registry with JSON Schema definitions,
ready to wire into any agent framework:

```python
from aidex.agent import list_tools, call_tool

tools = list_tools()
# [{"name": "count_tokens", "description": "...", "input_schema": {...}}, ...]

result = call_tool("count_tokens", {"text": "hello", "model": "gpt-4o"})
# {"model": "gpt-4o", "token_count": 1, "counting_method": "tiktoken",
#  "confidence": "exact"}
```

Arguments are validated with Pydantic; results are JSON-serializable dicts.
An MCP server is planned as an optional extra (`aidex mcp serve` is a stub in
v0.1).

## Tool reference

| Tool | Library function | CLI |
| --- | --- | --- |
| Token calculator | `aidex.tokens.count_tokens` | `aidex tokens count` |
| Cost estimator | `aidex.cost.estimate_cost` | `aidex cost estimate` |
| Context planner | `aidex.context.plan_context` | `aidex context plan` |
| Text chunker | `aidex.chunk.chunk_text` | `aidex chunk split` |
| JSON validator | `aidex.validate.json.validate_json` | `aidex validate json` |
| JSONL validator | `aidex.validate.jsonl.validate_jsonl` | `aidex validate jsonl` |
| CSV validator | `aidex.validate.csv_module.validate_csv` | `aidex validate csv` |
| PII redactor | `aidex.redact.redact_pii` | `aidex redact pii` |
| Diff checker | `aidex.diff.diff_text` | `aidex diff` |

Notes:

- **Chunker** uses recursive separator-aware splitting (`"\n\n"`, `"\n"`,
  `". "`, `" "` by default) and hard-splits at character boundaries as a last
  resort when no separator can satisfy the token budget.
- **JSON Schema validation** implements a dependency-free subset: `type`,
  `properties`, `required`, `items`, `enum`, `additionalProperties`,
  `minimum`/`maximum`, `minLength`/`maxLength`.
- **PII redaction** is regex-only in v0.1 (email, phone, SSN, credit card,
  IPv4, API keys). It is one-way: there is no unredact, and the audit trail
  records only type, span, and placeholder.
- **Model pricing** in `aidex models list` is a bundled snapshot for offline
  estimation; verify against provider pricing pages before billing decisions.

## Development

```bash
uv sync --extra dev
uv run pytest --cov=aidex
uv run ruff check .
uv run mypy src/aidex
uv run black --check .
```

## License

MIT
