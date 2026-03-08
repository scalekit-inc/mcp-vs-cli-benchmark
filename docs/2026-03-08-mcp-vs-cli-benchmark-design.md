# MCP vs CLI Benchmark: Design Document

> Pre-registered experimental design for comparing MCP servers against CLI tools
> when used by AI agents for the same tasks.

## Motivation

The AI tooling ecosystem is split: some services invest in MCP servers, some double
down on CLI tools, and some (like Google) actively remove MCP support. Developers and
engineering leaders need data — not opinions — to decide which approach works better
for their AI agent workflows.

This project runs a rigorous, reproducible benchmark comparing MCP and CLI across
three services, measuring performance, developer experience, and enterprise readiness.

## Services Under Test

| Service | CLI Tool | MCP Server | Why this pairing |
|---------|----------|------------|-----------------|
| **GitHub** | `gh` CLI (official) | GitHub MCP Server (official) | Fair fight. Both mature and official. The control case. |
| **Google Workspace** | `gwcli` (official, MCP removed) | Custom MCP via HTTP (Gateway) | Controversial. Google removed MCP support — we test what's lost. |
| **Postgres** | `psql` CLI | MCP Gateway server | Our home turf. Shows Gateway's value proposition. |

## Architecture

```
+--------------------------------------------------+
|              Benchmark Harness (Python)           |
|                                                   |
|  +------------+  +-----------+  +--------------+  |
|  |   Task     |  |  Runner   |  |  Metrics     |  |
|  |   Registry |  |  Engine   |  |  Collector   |  |
|  +-----+------+  +-----+-----+  +------+-------+  |
|        |              |               |            |
|        v              v               v            |
|  +------------------------------------------------+|
|  |           Claude API (Anthropic SDK)            ||
|  |         temperature=0, same model               ||
|  +----------+--------------------+------ ----------+|
|             |                    |                  |
|     +-------v------+   +--------v-------+          |
|     |  CLI Agent   |   |  MCP Agent     |          |
|     |  (tool_use   |   |  (tool_use     |          |
|     |   = bash)    |   |   = mcp)       |          |
|     +-------+------+   +--------+-------+          |
|             |                    |                  |
+-------------+--------------------+------------------+
              |                    |
      +-------v------+   +--------v-------+
      |  gh / psql / |   |  MCP Servers   |
      |  gwcli       |   |  (Gateway /    |
      |              |   |   GitHub /     |
      |              |   |   custom)      |
      +--------------+   +----------------+
```

### Key Design Decisions

- **Same model, same prompt**: Both agents receive identical system prompts and task
  descriptions. The only difference is the available tools.
- **CLI agent** gets a `bash` tool that can invoke `gh`, `psql`, `gwcli`.
- **MCP agent** gets tools exposed via MCP servers.
- **Claude API direct**: Raw API calls (Anthropic SDK), not Claude Code or any wrapper.
  Full control over instrumentation.
- **Temperature 0**: Maximizes reproducibility. Tool call variance still exists but is
  minimized.

## Task Design

Each service has 5 tasks at escalating complexity. Every task has a deterministic,
verifiable expected outcome.

### GitHub Tasks

| # | Task | Complexity | Verification |
|---|------|-----------|--------------|
| 1 | List open issues with label "bug" | Simple read | Compare issue IDs against ground truth |
| 2 | Get PR details including review comments | Multi-step read | Verify all fields present and correct |
| 3 | Create an issue with title, body, and labels | Simple write | Confirm issue exists via API |
| 4 | Find PRs by user merged in last 7 days, summarize | Complex read + reasoning | LLM-as-judge + verify PR list completeness |
| 5 | Create branch, commit file, open PR | Multi-step write | Verify branch, commit, PR exist |

### Google Workspace Tasks

| # | Task | Complexity | Verification |
|---|------|-----------|--------------|
| 1 | List files in a Drive folder | Simple read | Compare file list against ground truth |
| 2 | Read contents of a Google Doc | Simple read | Compare extracted text |
| 3 | Search Gmail for matching emails, return subjects | Filtered read | Verify subject list |
| 4 | Create a new Google Doc with structured content | Simple write | Verify doc exists with correct content |
| 5 | Find shared docs modified this week, summarize | Complex read + reasoning | LLM-as-judge + verify file list |

### Postgres Tasks

| # | Task | Complexity | Verification |
|---|------|-----------|--------------|
| 1 | List all tables in a schema | Simple read | Compare against information_schema |
| 2 | Run a SELECT query, return results | Simple read | Compare result set exactly |
| 3 | Describe table schema (columns, types, constraints) | Multi-step read | Verify against actual schema |
| 4 | Top 10 customers by revenue with 3-table join | Complex read + reasoning | Verify query correctness + results |
| 5 | Create table, insert data, create index, verify | Multi-step write | Verify all objects exist |

### Task Design Principles

- **Deterministic ground truth** for every task
- **No ambiguity** in task prompts — one right answer
- **Escalating complexity** to test multi-step workflow handling
- **Both read and write** tasks
- **Real-world relevance** — things developers actually do with agents

## Test Environment & Data Seeding

### Principle: Hermetic Test Fixtures

Both agents operate against identical, pre-seeded state. State is reset between every
run. No agent ever sees leftover state from a previous run.

### GitHub

- Dedicated test repo: public, so others can reproduce
- Seeded via GitHub API directly (not through either tool modality):
  - 10 issues with known labels, assignees, timestamps
  - 5 PRs (3 merged, 2 open) with review comments
  - Known branch structure
- Reset: teardown + re-create all objects using GitHub API before each run
- Write tasks namespaced with `bench/{run_id}/` to avoid collision

### Google Workspace

- Dedicated test Google account with known folder structure
- Seeded via Google Admin SDK / Drive API directly:
  - Folder with 10 known files (docs, sheets, PDFs)
  - 5 Gmail messages with known subjects, senders, dates
  - A specific Doc with known content
- Reset: delete all files in test folder, re-create from fixtures
- All operations scoped to a single test folder / label

### Postgres

- Fresh Docker container per run batch
- Seeded via SQL fixture file:
  ```sql
  DROP SCHEMA IF EXISTS benchmark CASCADE;
  CREATE SCHEMA benchmark;
  -- deterministic tables and data
  ```
- Reset: `DROP SCHEMA CASCADE` + re-run seed script
- Write tasks use `bench_{run_id}` schema

### Run Lifecycle

```
For each run:
  1. Generate unique run_id (UUID)
  2. Run seed script for all three services
  3. Verify seed state (assert expected objects exist)
  4. Execute CLI agent OR MCP agent (never both on same state)
  5. Capture all metrics
  6. Verify outcomes against ground truth
  7. Run teardown script
  8. Verify clean state
```

Runs alternate between CLI and MCP to avoid time-of-day bias:

```
Run 1:  seed -> CLI agent  -> verify -> teardown
Run 2:  seed -> MCP agent  -> verify -> teardown
Run 3:  seed -> CLI agent  -> verify -> teardown
Run 4:  seed -> MCP agent  -> verify -> teardown
...
```

## Statistical Methodology

### Sample Size

- **30 runs per agent per task** (minimum for CLT)
- 3 services x 5 tasks x 2 modalities x 30 runs = **900 total runs**

### Run Conditions

| Condition | Handling |
|-----------|----------|
| Cold start | First 3 runs flagged as "cold", reported independently |
| Warm start | Runs 4-30, server/CLI already initialized |
| Time-of-day | Alternate CLI/MCP runs, spread across hours |
| API latency | Record wall-clock AND token counts separately |
| Model non-determinism | Temperature=0 + 30 runs for statistical power |
| Task ordering | Randomized within each run |
| Context contamination | Fresh API conversation per run |

### Metrics

| Metric | Primary measure | Secondary measure |
|--------|----------------|-------------------|
| Token usage | Total tokens (input + output) | Input vs output breakdown |
| Tool call count | Number of tool_use blocks | Tool calls per task step |
| Task completion | Binary pass/fail | Partial completion score (0-1) |
| Latency | Wall-clock seconds | Tool execution time only |
| Error recovery | Retries before success | Self-correction (binary) |
| Tool discovery | Right tool on first try? | Exploratory calls before productive ones |
| Output quality | LLM-as-judge score (1-5) | Ground truth match % |

### Statistical Tests

For each metric, per task:

1. **Descriptive stats**: median, mean, std dev, min, max, P25, P75, P95
2. **Confidence intervals**: 95% CI on mean difference (CLI - MCP)
3. **Hypothesis test**: Paired Wilcoxon signed-rank test (non-parametric)
   - H0: No difference between CLI and MCP
   - H1: There is a difference
   - Significance: p < 0.05
4. **Effect size**: Cohen's d (practical significance, not just statistical)
5. **Multiple comparisons**: Bonferroni correction across 15 task comparisons

### LLM-as-Judge Protocol

- **Different model** as judge (e.g., benchmark with Sonnet, judge with Opus)
- Judge sees both outputs **side-by-side, randomly ordered, unlabeled**
- Each output judged **3 times**, majority vote
- Report inter-judge agreement (Fleiss' kappa)

### Pre-Registration

Hypotheses stated before running:

1. MCP will use fewer tokens than CLI (MCP returns structured data; CLI returns
   raw text that needs parsing)
2. CLI will have lower latency for simple tasks (no protocol overhead)
3. MCP will have higher task completion rate for complex multi-step tasks
   (better tool discovery, structured errors)
4. Cold start penalty will be higher for MCP (server initialization)

## Enterprise Analysis (Qualitative)

Not benchmarked with runs — demonstrated through implementation comparison.

### Access Control

| Scenario | CLI | MCP (Gateway) |
|----------|-----|---------------|
| Restrict to read-only | Read-only token. No enforcement layer. | Gateway exposes only read tools. |
| Per-user scoping | Each user manages own credentials | Gateway manages per-user, agent authenticates as itself |
| Revoke mid-session | Kill process or rotate token | Real-time revocation, graceful failure |
| Least privilege | Manual token scope crafting | Admin-configured tool-level access |

### Audit Trail

| Scenario | CLI | MCP (Gateway) |
|----------|-----|---------------|
| What did the agent do? | Parse shell history | Structured log: timestamp, user, tool, params, response |
| Who ran this? | Machine user | Authenticated identity per request |
| Compliance export | Build it yourself | Built-in retention + export |
| Alert on sensitive ops | DIY shell hooks | Gateway policy engine |

### Narrative Approach

Blog post walks through a realistic incident scenario:
> "Your intern's AI agent just dropped a production table. Let's trace what happened."

Show how CLI gives you nothing, Gateway gives full audit trail + could have prevented it.

## Project Structure

```
mcp-vs-cli-benchmark/
├── README.md
├── METHODOLOGY.md               # Pre-registered hypotheses
├── LICENSE                      # MIT
├── tasks/
│   ├── github/
│   │   ├── task_01_list_issues.yaml
│   │   └── ...
│   ├── google/
│   │   └── ...
│   └── postgres/
│       └── ...
├── fixtures/
│   ├── github_seed.py
│   ├── google_seed.py
│   ├── postgres_seed.sql
│   └── verify.py
├── agents/
│   ├── base.py                  # Claude API wrapper
│   ├── cli_agent.py             # CLI tool definitions
│   ├── mcp_agent.py             # MCP tool definitions
│   └── prompts/
│       └── system.md            # Identical system prompt
├── metrics/
│   ├── collector.py
│   ├── judge.py                 # LLM-as-judge
│   └── schemas.py               # Pydantic models
├── runner/
│   ├── harness.py               # Orchestrator
│   ├── config.py
│   └── scheduler.py             # Alternation + randomization
├── analysis/
│   ├── stats.py                 # Wilcoxon, Cohen's d, CIs
│   ├── visualize.py             # Charts
│   └── report.py                # Markdown report generator
├── results/
│   ├── raw/                     # Full API traces (JSON)
│   └── reports/                 # Generated reports
├── enterprise/
│   ├── access_control_demo.py
│   └── audit_trail_demo.py
└── content/
    ├── blog_01_benchmark.md     # Technical benchmark post
    └── blog_02_enterprise.md    # Enterprise implications post
```

## Deliverables

1. **Open-source repo** — fully reproducible benchmark framework
2. **Blog #1**: "MCP vs CLI: We Ran 900 Benchmarks So You Don't Have To" (developers)
3. **Blog #2**: "Your AI Agent Has Root Access. Now What?" (engineering leaders)
4. **Raw dataset** — all 900 runs with full API traces
5. **Summary infographic** — shareable visual for social media

## Phases

| Phase | Deliverable |
|-------|-------------|
| 1 | Framework scaffolding + GitHub benchmark (both modalities) |
| 2 | Add Google Workspace + Postgres benchmarks |
| 3 | Run full 900-run suite, statistical analysis |
| 4 | Enterprise access control + audit demos |
| 5 | Write + publish blog #1 (technical) |
| 6 | Write + publish blog #2 (enterprise) |

## What This Benchmark Does NOT Cover

- Performance of the underlying services themselves (GitHub API speed, etc.)
- Comparison across different LLM providers (Claude only)
- MCP server development effort (building vs configuring)
- Cost comparison beyond API token usage
- Agentic workflows with memory/planning across sessions

These are acknowledged limitations, not future work.
