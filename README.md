# MCP vs CLI Benchmark

Rigorous comparison of MCP servers vs CLI tools for AI agents.

## Key Findings

Results from a single run using Claude Sonnet 4 on 5 GitHub tasks:

| Task | CLI Tokens | MCP Tokens | CLI Calls | MCP Calls | CLI Time | MCP Time |
|------|-----------|-----------|-----------|-----------|----------|----------|
| Get repo info | 1,365 | 27,313 | 1 | 2 | 3.6s | 7.5s |
| Get PR details | 1,648 | 19,085 | 1 | 2 | 4.7s | 6.8s |
| Get repo metadata | 13,524 | 17,347 | 8 | 2 | 50.8s | 7.7s |
| Summarize PRs by contributor | 4,998 | 400,013 | 1 | 12 | 13.2s | 49.7s |
| Find release + dependencies | 8,750 | 134,736 | 3 | 2 | 9.0s | 10.8s |

## Key Insights

- **Token overhead:** MCP uses 1.3x to 80x more tokens than CLI, primarily due to tool schema overhead included in every request.
- **Tool call patterns:** CLI often needs more tool calls for complex tasks due to trial-and-error with `gh` commands, while MCP typically resolves in fewer calls via direct API access.
- **Latency tradeoffs:** MCP is faster on structured data tasks (direct API access vs parsing CLI output), but CLI wins on simple lookups where a single shell command suffices.
- **Task completion:** Both modalities achieve 100% task completion on all 5 GitHub tasks.

## Quick Start

```bash
git clone https://github.com/scalekit-inc/mcp-vs-cli-benchmark.git
cd mcp-vs-cli-benchmark
cp .env.example .env  # Add your API keys
uv sync
uv run bench run --runs 1 --clean
uv run bench analyze --input results/raw
```

## Configuration

All configuration is done via environment variables in `.env`:

| Variable | Description | Example |
|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | Anthropic API key for Claude models | `sk-ant-...` |
| `OPENAI_API_KEY` | OpenAI API key (optional, for GPT models) | `sk-...` |
| `GEMINI_API_KEY` | Google Gemini API key (optional) | `AIza...` |
| `BENCHMARK_MODEL` | Model to benchmark, in LiteLLM format | `anthropic/claude-sonnet-4-20250514` |
| `JUDGE_MODEL` | Model used for LLM-as-judge evaluation | `anthropic/claude-opus-4-20250514` |
| `GITHUB_TOKEN` | GitHub personal access token for API tasks | `ghp_...` |
| `BENCHMARK_REPO` | Target repository for benchmark tasks | `your-org/repo` |
| `MCP_GITHUB_SERVER_URL` | URL of the MCP GitHub server | (local or remote URL) |
| `POSTGRES_URL` | PostgreSQL connection string (for DB tasks) | `postgresql://bench:bench@localhost:5432/benchmark` |

## CLI Usage

The benchmark CLI is invoked via `uv run bench`. It has two subcommands: `run` and `analyze`.

### `bench run`

Run benchmark tasks against one or both modalities.

```bash
# Run all tasks, 30 runs each (default)
uv run bench run --runs 30

# Run a single task
uv run bench run --task github_01 --runs 5

# Run only the CLI modality
uv run bench run --modality cli --runs 10

# Run only the MCP modality
uv run bench run --modality mcp --runs 10

# Use a specific model
uv run bench run --model anthropic/claude-sonnet-4-20250514 --runs 5

# Clear previous results before running
uv run bench run --runs 1 --clean
```

**Flags:**

| Flag | Default | Description |
|------|---------|-------------|
| `--runs N` | 30 | Number of runs per task per modality |
| `--task ID` | all | Run only a specific task (e.g., `github_01`) |
| `--modality` | both | Run only `cli` or `mcp` |
| `--model` | `$BENCHMARK_MODEL` | LiteLLM model identifier |
| `--clean` | false | Clear previous results before running |
| `--seed N` | none | Random seed for reproducibility |
| `--output DIR` | `results/raw` | Output directory for raw results |
| `--service` | `github` | Service(s) to benchmark |

### `bench analyze`

Generate reports and charts from raw results.

```bash
# Analyze results in the default directory
uv run bench analyze --input results/raw

# Analyze results from a custom directory
uv run bench analyze --input path/to/results
```

This produces a Markdown report at `results/reports/report.md` and charts in `results/charts/`.

## Architecture

The benchmark is organized into four layers:

1. **Agents** -- Two agent implementations (`cli` and `mcp`) that perform identical tasks using different tool interfaces. The CLI agent invokes shell commands (e.g., `gh`); the MCP agent connects to an MCP server for structured API access.
2. **Harness** -- The runner that orchestrates task execution, manages agent lifecycles, and collects raw metrics for each run.
3. **Metrics** -- Token counts, tool call counts, wall-clock time, and task correctness (verified by an LLM-as-judge) are recorded per run.
4. **Analysis** -- Statistical analysis pipeline that computes summary statistics, runs paired comparisons, and generates charts and Markdown reports.

## Methodology

The experimental design follows pre-registered hypotheses and statistical methods documented in [METHODOLOGY.md](METHODOLOGY.md). Key points:

- Hypotheses were written and committed before any benchmarks were run.
- 30 runs per agent per task (minimum for CLT) for statistical validity.
- Paired Wilcoxon signed-rank test with Bonferroni correction (p < 0.05).
- Effect sizes reported via Cohen's d alongside all p-values.
- LLM-as-judge for task correctness evaluation.

## Contributing

Contributions are welcome. To get started:

1. Fork the repository and create a feature branch.
2. Install dependencies: `uv sync`
3. Run tests: `uv run pytest`
4. Ensure your changes pass type checking: `uv run mypy src/`
5. Submit a pull request with a clear description of your changes.

Please open an issue first for large changes or new task definitions.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
