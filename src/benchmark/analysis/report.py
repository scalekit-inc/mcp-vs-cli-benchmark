"""Generate analysis reports from benchmark results."""

from collections import defaultdict
from pathlib import Path

from benchmark.analysis.stats import ComparisonResult, compare_metric
from benchmark.metrics.schemas import RunResult


def load_results(results_dir: Path) -> list[RunResult]:
    """Load all RunResult JSON files from a directory."""
    results = []
    for path in sorted(results_dir.glob("*.json")):
        results.append(RunResult.model_validate_json(path.read_text()))
    return results


def group_by_task(
    results: list[RunResult],
) -> dict[str, dict[str, list[RunResult]]]:
    """Group results by task_id, then by modality."""
    grouped: dict[str, dict[str, list[RunResult]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for r in results:
        grouped[r.task_id][r.modality].append(r)
    return dict(grouped)


def analyze_task(
    task_id: str, cli_runs: list[RunResult], mcp_runs: list[RunResult]
) -> dict[str, ComparisonResult]:
    """Analyze all metrics for a single task."""
    comparisons: dict[str, ComparisonResult] = {}

    # Token usage
    cli_tokens = [float(r.total_tokens) for r in cli_runs]
    mcp_tokens = [float(r.total_tokens) for r in mcp_runs]
    if cli_tokens and mcp_tokens:
        comparisons["total_tokens"] = compare_metric(
            "total_tokens", cli_tokens, mcp_tokens
        )

    # Tool call count
    cli_tc = [float(r.tool_call_count) for r in cli_runs]
    mcp_tc = [float(r.tool_call_count) for r in mcp_runs]
    if cli_tc and mcp_tc:
        comparisons["tool_calls"] = compare_metric("tool_calls", cli_tc, mcp_tc)

    # Wall clock time
    cli_wc = [r.wall_clock_seconds for r in cli_runs]
    mcp_wc = [r.wall_clock_seconds for r in mcp_runs]
    if cli_wc and mcp_wc:
        comparisons["wall_clock"] = compare_metric("wall_clock", cli_wc, mcp_wc)

    # Completion rate
    cli_comp = [1.0 if r.task_completed else 0.0 for r in cli_runs]
    mcp_comp = [1.0 if r.task_completed else 0.0 for r in mcp_runs]
    if cli_comp and mcp_comp:
        comparisons["completion"] = compare_metric("completion", cli_comp, mcp_comp)

    return comparisons


def generate_markdown_report(results_dir: Path) -> str:
    """Generate a full markdown analysis report."""
    results = load_results(results_dir)
    if not results:
        return "# Benchmark Report\n\nNo results found.\n"

    grouped = group_by_task(results)

    lines = [
        "# MCP vs CLI Benchmark Report\n",
        f"**Total runs:** {len(results)}",
        f"**Tasks:** {len(grouped)}",
        f"**Model:** {results[0].model if results else 'unknown'}",
        "",
    ]

    all_comparisons: list[ComparisonResult] = []

    for task_id in sorted(grouped.keys()):
        cli_runs = grouped[task_id].get("cli", [])
        mcp_runs = grouped[task_id].get("mcp", [])

        # Use task_name from first available result, fall back to task_id
        all_runs = cli_runs + mcp_runs
        task_name = next((r.task_name for r in all_runs if r.task_name), task_id)
        lines.append(f"## {task_name} (`{task_id}`)\n")
        lines.append(f"CLI runs: {len(cli_runs)} | MCP runs: {len(mcp_runs)}\n")

        if not cli_runs or not mcp_runs:
            lines.append("*Skipped -- need both modalities to compare.*\n")
            continue

        comparisons = analyze_task(task_id, cli_runs, mcp_runs)

        lines.append(
            "| Metric | CLI (median) | MCP (median) | Diff (mean) "
            "| p-value | Cohen's d | Winner |"
        )
        lines.append(
            "|--------|-------------|-------------|-------------|"
            "---------|-----------|--------|"
        )

        for name, comp in comparisons.items():
            p_str = f"{comp.p_value:.4f}" if comp.p_value is not None else "n/a"
            lines.append(
                f"| {comp.metric} | {comp.cli_median:.1f} | {comp.mcp_median:.1f} | "
                f"{comp.mean_diff:+.1f} | {p_str} | {comp.cohens_d:.2f} | {comp.winner} |"
            )
            all_comparisons.append(comp)

        lines.append("")

    # Summary
    if all_comparisons:
        cli_wins = sum(1 for c in all_comparisons if c.winner == "cli")
        mcp_wins = sum(1 for c in all_comparisons if c.winner == "mcp")
        ties = sum(1 for c in all_comparisons if c.winner == "tie")

        lines.append("## Summary\n")
        lines.append(f"- CLI wins: {cli_wins}")
        lines.append(f"- MCP wins: {mcp_wins}")
        lines.append(f"- Ties: {ties}")

    return "\n".join(lines) + "\n"
