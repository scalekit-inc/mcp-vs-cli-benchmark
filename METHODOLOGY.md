# Pre-Registered Methodology

> This document was written and committed BEFORE running any benchmarks.
> It constitutes our pre-registration of hypotheses and methods.

## Hypotheses

1. **H1 (Token Efficiency):** MCP agents will use fewer total tokens than CLI agents
   for the same tasks, because MCP returns structured data while CLI returns raw
   terminal output that requires parsing.

2. **H2 (Simple Task Latency):** CLI agents will complete simple read tasks faster
   (wall-clock) than MCP agents, due to lower protocol overhead.

3. **H3 (Complex Task Completion):** MCP agents will have a higher task completion
   rate on complex multi-step tasks (complexity: complex_read, multi_step_write),
   because structured tool interfaces reduce ambiguity and error rates.

4. **H4 (Cold Start):** MCP agents will exhibit a larger cold-start latency penalty
   than CLI agents, because MCP servers require initialization.

## Statistical Methods

- **Sample size:** 30 runs per agent per task (minimum for CLT).
- **Test:** Paired Wilcoxon signed-rank test (non-parametric, two-sided).
- **Significance:** p < 0.05 after Bonferroni correction (15 comparisons).
- **Effect size:** Cohen's d reported alongside all p-values.
- **Confidence intervals:** 95% CI on mean difference (CLI - MCP).

## LLM-as-Judge

- Judge model differs from benchmark model (benchmark: Sonnet, judge: Opus).
- Outputs presented side-by-side, randomly ordered, without modality labels.
- Each pair judged 3 times; majority vote determines final score.
- Inter-judge agreement reported via Fleiss' kappa.

## Run Conditions

- Temperature: 0 for all benchmark runs.
- Runs alternate between CLI and MCP to control for time-of-day effects.
- Task order randomized within each run.
- Each run uses a fresh API conversation (no shared context).
- First 3 runs per modality flagged as cold starts, analyzed separately.

## What We Will Report

For each metric (tokens, tool calls, latency, completion, quality):
- Descriptive statistics: median, mean, std dev, P25, P75, P95
- Statistical test results with exact p-values
- Effect sizes (Cohen's d)
- Confidence intervals
- Visualization: box plots + strip plots overlaid

## Limitations (Known Before Running)

- Single LLM provider (Anthropic Claude); results may not generalize to others.
- CLI tools tested in macOS environment; behavior may differ on Linux.
- MCP servers tested locally (HTTP transport); remote deployment may differ.
- Fixture data is synthetic; real-world data may produce different patterns.
- 30 runs provides moderate statistical power; rare failure modes may be missed.
