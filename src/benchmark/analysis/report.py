"""Generate analysis reports from benchmark results."""

from collections import defaultdict
from itertools import combinations
from pathlib import Path

import numpy as np

from benchmark.analysis.stats import ComparisonResult, compare_metric
from benchmark.metrics.schemas import RunResult

MODALITY_ORDER = ["cli", "cli_skilled", "mcp", "gateway"]
MODALITY_LABELS = {
    "cli": "CLI",
    "cli_skilled": "CLI+Skills",
    "mcp": "MCP",
    "gateway": "Gateway",
}


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


def _detect_modalities(results: list[RunResult]) -> list[str]:
    """Return ordered list of modalities present in results."""
    seen = {r.modality for r in results}
    return [m for m in MODALITY_ORDER if m in seen]


def _extract_metric(runs: list[RunResult], metric: str) -> list[float]:
    """Extract a metric as a list of floats from runs."""
    if metric == "total_tokens":
        return [float(r.total_tokens) for r in runs]
    elif metric == "tool_calls":
        return [float(r.tool_call_count) for r in runs]
    elif metric == "wall_clock":
        return [r.wall_clock_seconds for r in runs]
    elif metric == "completion":
        return [1.0 if r.task_completed else 0.0 for r in runs]
    return []


def generate_markdown_report(results_dir: Path) -> str:
    """Generate a full markdown analysis report."""
    results = load_results(results_dir)
    if not results:
        return "# Benchmark Report\n\nNo results found.\n"

    grouped = group_by_task(results)
    modalities = _detect_modalities(results)

    lines = [
        "# MCP vs CLI Benchmark Report\n",
        f"**Total runs:** {len(results)}",
        f"**Tasks:** {len(grouped)}",
        f"**Modalities:** {', '.join(MODALITY_LABELS.get(m, m) for m in modalities)}",
        f"**Model:** {results[0].model if results else 'unknown'}",
        "",
    ]

    # Per-task summary table
    for task_id in sorted(grouped.keys()):
        task_modalities = grouped[task_id]
        all_runs = [r for runs in task_modalities.values() for r in runs]
        task_name = next((r.task_name for r in all_runs if r.task_name), task_id)

        lines.append(f"## {task_name} (`{task_id}`)\n")

        # Run counts
        counts = " | ".join(
            f"{MODALITY_LABELS.get(m, m)}: {len(task_modalities.get(m, []))}"
            for m in modalities if m in task_modalities
        )
        lines.append(f"{counts}\n")

        # Metrics overview table
        present = [m for m in modalities if task_modalities.get(m)]
        if len(present) < 2:
            lines.append("*Need at least 2 modalities to compare.*\n")
            continue

        metrics = ["total_tokens", "tool_calls", "wall_clock", "completion"]
        header_cols = ["Metric"] + [MODALITY_LABELS.get(m, m) for m in present]
        lines.append("| " + " | ".join(header_cols) + " |")
        lines.append("|" + "|".join(["--------"] * len(header_cols)) + "|")

        for metric in metrics:
            row = [metric]
            for m in present:
                vals = _extract_metric(task_modalities[m], metric)
                if vals:
                    med = float(np.median(vals))
                    row.append(f"{med:.1f}")
                else:
                    row.append("n/a")
            lines.append("| " + " | ".join(row) + " |")

        lines.append("")

    # Pairwise comparisons
    if len(modalities) >= 2:
        lines.append("## Pairwise Comparisons\n")

        all_comparisons: list[ComparisonResult] = []

        for m1, m2 in combinations(modalities, 2):
            label1 = MODALITY_LABELS.get(m1, m1)
            label2 = MODALITY_LABELS.get(m2, m2)
            lines.append(f"### {label1} vs {label2}\n")

            has_data = False
            for task_id in sorted(grouped.keys()):
                runs1 = grouped[task_id].get(m1, [])
                runs2 = grouped[task_id].get(m2, [])
                if not runs1 or not runs2:
                    continue

                if not has_data:
                    lines.append(
                        f"| Task | Metric | {label1} (median) | {label2} (median) "
                        f"| Diff (mean) | p-value | Cohen's d | Winner |"
                    )
                    lines.append(
                        "|------|--------|" + "-------------|" * 2
                        + "-------------|---------|-----------|--------|"
                    )
                    has_data = True

                for metric in ["total_tokens", "tool_calls", "wall_clock"]:
                    vals1 = _extract_metric(runs1, metric)
                    vals2 = _extract_metric(runs2, metric)
                    if vals1 and vals2:
                        comp = compare_metric(metric, vals1, vals2, label_a=label1, label_b=label2)
                        p_str = f"{comp.p_value:.4f}" if comp.p_value is not None else "n/a"
                        lines.append(
                            f"| {task_id} | {metric} | {comp.cli_median:.1f} "
                            f"| {comp.mcp_median:.1f} | {comp.mean_diff:+.1f} "
                            f"| {p_str} | {comp.cohens_d:.2f} | {comp.winner} |"
                        )
                        all_comparisons.append(comp)

            if not has_data:
                lines.append("*No overlapping task data.*\n")
            lines.append("")

        # Summary
        if all_comparisons:
            lines.append("## Summary\n")
            win_counts: dict[str, int] = {}
            ties = 0
            for c in all_comparisons:
                if c.winner == "tie":
                    ties += 1
                else:
                    win_counts[c.winner] = win_counts.get(c.winner, 0) + 1
            for label in [MODALITY_LABELS.get(m, m) for m in modalities]:
                count = win_counts.get(label, 0)
                if count > 0:
                    lines.append(f"- **{label}** wins: {count}")
            lines.append(f"- Ties: {ties}")

    return "\n".join(lines) + "\n"
