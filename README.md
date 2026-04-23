# Promptinear

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](./LICENSE)
[![Tests](https://img.shields.io/badge/tests-pytest-orange.svg)](#testing)

**Bring-your-own-LLM prompt efficiency grader.** A polished terminal application that scores your AI prompts across six dimensions, estimates wasted tokens and dollars, and coaches you on where to improve.

Promptinear is designed for engineers and enterprise teams who want to cut LLM spend by writing tighter, higher-leverage prompts. Plug in your own OpenAI, Anthropic, or Gemini key - or point it at a local model via Ollama, LM Studio, or any OpenAI-compatible endpoint. No vendor lock-in, no telemetry, no account required.

## Highlights

- **Six-dimension rubric** - Clarity, Context, Structure, Actionability, Efficiency, Grounding
- **Pluggable LLM providers** - OpenAI, Anthropic, Gemini, and any OpenAI-compatible endpoint (Ollama, LM Studio, OpenRouter, vLLM)
- **Zero-key fallback** - Ships with a deterministic heuristic analyzer so the app is fully usable without any API access
- **Full TUI** - Syntax-aware panels, live progress, keyboard-driven navigation, dashboard with trends
- **CLI-friendly** - Every feature is also a subcommand; pipe prompts through stdin, export JSON/Markdown/CSV
- **Versioned history** - Local `history.json` tracks your improvement over time with auto-migration
- **Public-repo safe** - Secrets loaded from env or a 0600 config file; never committed

## Install

```bash
git clone https://github.com/landon/promptinear.git
cd promptinear
pip install -e .
promptinear
```

Or install with dev extras for running the test suite:

```bash
pip install -e ".[dev]"
pytest
```

## Quick start

Launch the TUI (default):

```bash
promptinear
```

Analyze a single prompt from the command line:

```bash
echo "fix the bug in the parser" | promptinear analyze --stdin
```

Show your history summary:

```bash
promptinear history --limit 10
```

Inspect or change configuration:

```bash
promptinear config show
promptinear config set provider openai
promptinear config set model gpt-4o-mini
```

## Bring your own LLM

Promptinear never ships with an API key. You configure one of four modes:

### 1. Heuristic (default, no network)

A deterministic rule-based scorer. Fastest, free, offline.

```bash
promptinear analyze --provider heuristic
```

### 2. OpenAI or any compatible endpoint

```bash
export OPENAI_API_KEY=sk-...
promptinear analyze --provider openai --model gpt-4o-mini
```

For a local model, point at an OpenAI-compatible base URL:

```bash
# Ollama
export OPENAI_BASE_URL=http://localhost:11434/v1
promptinear analyze --provider openai-compat --model llama3.1

# LM Studio
export OPENAI_BASE_URL=http://localhost:1234/v1

# OpenRouter
export OPENAI_BASE_URL=https://openrouter.ai/api/v1
export OPENAI_API_KEY=sk-or-...
```

### 3. Anthropic (Claude)

```bash
export ANTHROPIC_API_KEY=sk-ant-...
promptinear analyze --provider anthropic --model claude-opus-4-7
```

### 4. Google Gemini

```bash
export GEMINI_API_KEY=...
promptinear analyze --provider gemini --model gemini-2.5-flash
```

### Persistent config

Instead of environment variables, you can write settings to `~/.promptinear/config.toml`:

```toml
provider = "openai"
model    = "gpt-4o-mini"
api_key  = "sk-..."           # optional; if omitted, read from env
base_url = ""                 # optional; for OpenAI-compatible endpoints
timeout  = 15
```

The file is written with `0600` permissions. Use `promptinear config set` to update it safely.

## Scoring

Each prompt receives a 0–100 score on six dimensions:

| Dimension      | What it measures                                                         |
| -------------- | ------------------------------------------------------------------------ |
| Clarity        | Precision of language; absence of hedging and ambiguity                  |
| Context        | Presence of the situation, current state, and expected outcome           |
| Structure      | Formatting - numbered steps, code fences, sections                       |
| Actionability  | Explicit verbs; a concrete task the model can execute                    |
| Efficiency     | Signal-to-filler ratio; every token should carry information             |
| Grounding      | References to real artifacts - file paths, function names, error text   |

The overall grade is the curved average of the six dimensions. See [`src/promptinear/scoring.py`](src/promptinear/scoring.py) for the curve formula.

## Screens

- **Analyze** - Paste a prompt, watch live bars fill in per dimension, drill into weak areas for coaching
- **History** - Timeline of past analyses with trend sparkline and summary stats
- **Dashboard** - Grade distribution, weakest-area counts, token-waste totals, trend chart
- **Settings** - Change provider, model, and API key inline; test connectivity
- **Help** - Key bindings and the prompt checklist

## Architecture

```
src/promptinear/
  cli.py           CLI entry point (argparse subcommands)
  config.py        Env + TOML config resolver
  models.py        Frozen dataclasses for domain types
  scoring.py       Grade curve, letter grades, token/cost estimation
  storage.py       Versioned history persistence
  analyzers/       Heuristic + LLM-backed scoring
  providers/       Plugin registry + OpenAI / Anthropic / Gemini clients
  tui/             Rich-powered terminal UI
```

All modules are type-hinted and tested with pytest.

## Testing

```bash
pytest                          # full suite
pytest --cov=promptinear         # with coverage report
ruff check src tests            # lint
mypy src                        # static types
```

All HTTP calls in tests are served by `httpx.MockTransport` - no real network traffic.

## Privacy

- Promptinear sends your prompt **only** to the provider you configured, and **only** when you request an analysis.
- Nothing is sent to any Promptinear-owned endpoint; there is none.
- History lives in `./history.json` next to your working directory by default, and can be moved with `--history-path`.

## Contributing

Issues and pull requests welcome. Please run `pytest`, `ruff check`, and `mypy src` before submitting. The module map lives under [`src/promptinear/`](src/promptinear/).

## License

MIT - see [LICENSE](./LICENSE).
