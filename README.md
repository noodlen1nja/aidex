# Aidex

**Offline AI developer tooling that runs with zero network calls and drops
straight into an agent.** Token counting, cost estimation, context-window
planning, text chunking, data validation, PII redaction, and diffing — one
package, exposed three ways: a Python library, a CLI, and an agent tool
registry with JSON Schemas.

No API keys. No HTTP clients in core. Works in air-gapped CI, locked-down
enterprise environments, and pre-commit hooks where calling out to a pricing
or tokenization API isn't an option.

Aidex deliberately makes a different trade than the cost-calculator crowd: it
never calls the network, so its model pricing is a **bundled snapshot** rather
than live data. When that snapshot goes stale, you override it locally without
waiting for a release — see [Custom & updated pricing](#custom--updated-pricing).
Non-OpenAI token counts are character heuristics labeled `estimate`, never
presented as exact (see [Confidence labeling](#confidence-labeling-honesty-is-mandatory)).

> **Naming note:** this package is published on PyPI as **`aidex-tools`** (the
> CLI command is `aidex-tools`, the import path is `aidex`).

> **Note on tiktoken:** OpenAI token counting uses
> [tiktoken](https://github.com/openai/tiktoken), which downloads its encoding
> files once on first use and caches them locally. After that first run,
> everything is fully offline.

## Install

```bash
pip install aidex-tools
# or
uv add aidex-tools
```

Requires Python >= 3.11.

## Quickstart (library)

The import path is `aidex`:

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
cost = estimate_cost("some prompt", model="claude-sonnet-4-6", output_tokens=500)
print(f"${cost.total_cost_usd:.6f} ({cost.confidence})")

# Will it fit?
plan = plan_context(open("examples/big_doc.txt").read(), model="gpt-4o")
if not plan.fits and plan.suggestion:
    print(f"Chunk into ~{plan.suggestion.estimated_chunks} pieces")

# Chunk it
chunks = chunk_text(
    open("examples/big_doc.txt").read(), max_tokens=512, overlap_tokens=50
)

# Redact PII (one-way; audit trail never contains original values)
redacted = redact_pii("Contact bob@example.com or 555-867-5309")
print(redacted.redacted_text)  # Contact [EMAIL] or [PHONE]
```

Every public function returns a Pydantic model that serializes cleanly to
JSON — the same shapes the CLI emits with `--json` and the agent registry
returns from `call_tool`.

## Confidence labeling

Token counts are only exact when the tokenizer is public. Aidex never
presents an estimate as exact:

| Provider | Counting method | Confidence |
| --- | --- | --- |
| OpenAI (gpt-5.5, gpt-5.4, gpt-4o, …) | tiktoken | `exact` |
| Anthropic, Google, others | per-provider character heuristic | `estimate` |

Every result — token counts, costs, context plans, chunks, token deltas —
carries a `confidence` field, and CLI comparison tables show a Confidence
column.

### Heuristic accuracy

For models without a public tokenizer, Aidex estimates `characters ÷
chars_per_token`. The divisor is **per provider**, not a flat `4`, because
tokenizers differ: Claude's runs denser than GPT's (more tokens, fewer
characters each), so a flat `÷4` understates Claude usage. Defaults are
rough English-prose averages (Claude ≈ 3.5, Gemini ≈ 4.0); they are still
estimates and remain labeled `estimate`.

You can tune the divisor per model with a `chars_per_token` field in your
[external models file](#custom--updated-pricing) — useful if you measure
your own corpus (code and non-English text tokenize differently from prose).

## Custom & updated pricing

The bundled model catalog is a point-in-time snapshot. Because Aidex never
calls the network, new model launches and price changes don't reach it until
the next release — so you can override the catalog locally instead of waiting.

Point `AIDEX_MODELS_FILE` (or the `--models-file` CLI flag) at a JSON file using
the same shape as the bundle. Entries are **merged over** the bundled catalog:

- a model whose `id` matches a bundled one **replaces** that entry (full entry),
- new ids are **added** (handy for private models or fine-tunes),
- an optional `default_comparison_set` overrides the default comparison list.

```json
{
  "default_comparison_set": ["gpt-5.5", "my-finetune"],
  "models": [
    {
      "id": "gpt-5.5",
      "aliases": [],
      "context_window": 1050000,
      "input_price_per_1m": 4.0,
      "output_price_per_1m": 24.0,
      "counting_method": "tiktoken",
      "confidence": "exact"
    },
    {
      "id": "my-finetune",
      "aliases": ["ft"],
      "context_window": 32000,
      "input_price_per_1m": 0.5,
      "output_price_per_1m": 1.5,
      "counting_method": "heuristic",
      "confidence": "estimate",
      "chars_per_token": 3.7
    }
  ]
}
```

The optional `chars_per_token` tunes the heuristic divisor for that model
(see [Heuristic accuracy](#heuristic-accuracy)); omit it to use the
per-provider default inferred from the model id.

```bash
# via flag (applies to every subcommand)
aidex-tools --models-file ./my_models.json cost estimate prompt.txt --model gpt-5.5

# or via environment variable
export AIDEX_MODELS_FILE=./my_models.json
aidex-tools models list
```

From the library, set the env var before the catalog is first read. The catalog
is process-cached; if you change it mid-process, call
`aidex.models.load_catalog.cache_clear()`.

## CLI

Every subcommand supports `--json` for machine-readable output. Exit codes:
`0` success, `1` runtime/validation error, `2` usage error. Errors go to
stderr (as `{"error": "...", "code": "..."}` in `--json` mode).

```bash
aidex-tools tokens count "How many tokens is this?"        # compare 6 models
aidex-tools tokens count examples/prompt.txt --model gpt-4o --json

aidex-tools cost estimate examples/prompt.txt --model claude-sonnet-4-6 --output-tokens 1000

aidex-tools context plan examples/big_doc.txt --model gpt-4o --reserve-output 4096

aidex-tools chunk split examples/big_doc.txt --max-tokens 512 --overlap 50

aidex-tools validate json examples/config.json --schema examples/schema.json
aidex-tools validate jsonl examples/dataset.jsonl --check-keys
aidex-tools validate csv examples/data.csv --no-header

aidex-tools redact pii "email bob@example.com, key sk-abc123def456ghi789" \
    --patterns email,api_key

aidex-tools diff examples/old_prompt.txt examples/new_prompt.txt --model gpt-4o

aidex-tools models list
aidex-tools models show claude-sonnet-4-6
aidex-tools tools list
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
An MCP server is planned as an optional extra (`aidex-tools mcp serve` is a
stub in v0.1).

> **Heads-up for agent integrations:** `diff_text` and `validate_json` accept
> either literal text or a file path — a string argument naming an existing
> file is read from disk. If tool arguments come from an untrusted source,
> treat this as a local file read capability.

## Tool reference

| Tool | Library function | CLI |
| --- | --- | --- |
| Token calculator | `aidex.tokens.count_tokens` | `aidex-tools tokens count` |
| Cost estimator | `aidex.cost.estimate_cost` | `aidex-tools cost estimate` |
| Context planner | `aidex.context.plan_context` | `aidex-tools context plan` |
| Text chunker | `aidex.chunk.chunk_text` | `aidex-tools chunk split` |
| JSON validator | `aidex.validate.json.validate_json` | `aidex-tools validate json` |
| JSONL validator | `aidex.validate.jsonl.validate_jsonl` | `aidex-tools validate jsonl` |
| CSV validator | `aidex.validate.csv_module.validate_csv` | `aidex-tools validate csv` |
| PII redactor | `aidex.redact.redact_pii` | `aidex-tools redact pii` |
| Diff checker | `aidex.diff.diff_text` | `aidex-tools diff` |

Notes:

- **Chunker** uses recursive separator-aware splitting (`"\n\n"`, `"\n"`,
  `". "`, `" "` by default) and hard-splits at character boundaries as a last
  resort when no separator can satisfy the token budget.
- **JSON Schema validation** implements a dependency-free subset: `type`,
  `properties`, `required`, `items`, `enum`, `additionalProperties`,
  `minimum`/`maximum`, `minLength`/`maxLength`.
- **PII redaction** is a best-effort, regex-only scrubber in v0.1 (email,
  phone, SSN, credit card, IPv4, API keys). It catches known token shapes,
  not names, addresses, or contextual PII — do not treat it as a compliance
  control. It is one-way: there is no unredact, and the audit trail records
  only type, span, and placeholder.
- **Model pricing** in `aidex-tools models list` is a bundled snapshot for
  offline estimation; verify against provider pricing pages before billing
  decisions, and override it locally via
  [Custom & updated pricing](#custom--updated-pricing) when it goes stale.

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
