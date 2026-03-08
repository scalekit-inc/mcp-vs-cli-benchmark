# MCP vs CLI Benchmark

Rigorous benchmark comparing MCP servers vs CLI tools for AI agents.

See [METHODOLOGY.md](METHODOLOGY.md) for the pre-registered experimental design.

## Setup

```bash
uv sync --all-extras
cp .env.example .env
# Fill in API keys
```

## Run

```bash
uv run bench run --service github --runs 30
uv run bench analyze --input results/raw/
```
