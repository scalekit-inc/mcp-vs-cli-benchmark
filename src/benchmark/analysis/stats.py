"""Statistical analysis for benchmark comparisons."""

from dataclasses import dataclass

import numpy as np
from scipy import stats as sp_stats


@dataclass
class ComparisonResult:
    """Result of comparing CLI vs MCP for a single metric."""

    metric: str
    cli_mean: float
    cli_median: float
    cli_std: float
    cli_p25: float
    cli_p75: float
    cli_p95: float
    mcp_mean: float
    mcp_median: float
    mcp_std: float
    mcp_p25: float
    mcp_p75: float
    mcp_p95: float
    mean_diff: float  # cli - mcp (positive = CLI higher)
    ci_lower: float  # 95% CI lower bound on mean diff
    ci_upper: float  # 95% CI upper bound on mean diff
    wilcoxon_statistic: float | None
    p_value: float | None  # None if sample too small
    cohens_d: float  # effect size
    winner: str  # "cli", "mcp", or "tie"


def descriptive_stats(values: list[float]) -> dict:
    """Compute descriptive statistics for a list of values."""
    arr = np.array(values)
    return {
        "mean": float(np.mean(arr)),
        "median": float(np.median(arr)),
        "std": float(np.std(arr, ddof=1)) if len(arr) > 1 else 0.0,
        "min": float(np.min(arr)),
        "max": float(np.max(arr)),
        "p25": float(np.percentile(arr, 25)),
        "p75": float(np.percentile(arr, 75)),
        "p95": float(np.percentile(arr, 95)),
    }


def cohens_d(group1: list[float], group2: list[float]) -> float:
    """Compute Cohen's d effect size between two groups."""
    n1, n2 = len(group1), len(group2)
    if n1 < 2 or n2 < 2:
        return 0.0
    var1 = float(np.var(group1, ddof=1))
    var2 = float(np.var(group2, ddof=1))
    pooled_std = np.sqrt(((n1 - 1) * var1 + (n2 - 1) * var2) / (n1 + n2 - 2))
    if pooled_std == 0:
        return 0.0
    return float((np.mean(group1) - np.mean(group2)) / pooled_std)


def wilcoxon_test(
    group1: list[float], group2: list[float]
) -> tuple[float | None, float | None]:
    """Paired Wilcoxon signed-rank test.

    Returns (statistic, p_value) or (None, None) if not enough data.
    """
    if len(group1) != len(group2) or len(group1) < 6:
        return None, None
    diffs = [a - b for a, b in zip(group1, group2)]
    if all(d == 0 for d in diffs):
        return None, None
    try:
        stat, p = sp_stats.wilcoxon(group1, group2, alternative="two-sided")
        return float(stat), float(p)
    except Exception:
        return None, None


def confidence_interval_95(
    group1: list[float], group2: list[float]
) -> tuple[float, float]:
    """95% confidence interval on the mean difference (group1 - group2)."""
    diffs = [a - b for a, b in zip(group1, group2)]
    n = len(diffs)
    if n < 2:
        return (0.0, 0.0)
    mean_diff = float(np.mean(diffs))
    se = float(np.std(diffs, ddof=1) / np.sqrt(n))
    t_crit = float(sp_stats.t.ppf(0.975, df=n - 1))
    return (mean_diff - t_crit * se, mean_diff + t_crit * se)


def bonferroni_correct(
    p_values: list[float | None], num_comparisons: int | None = None
) -> list[float | None]:
    """Apply Bonferroni correction to a list of p-values."""
    n = num_comparisons or len([p for p in p_values if p is not None])
    return [min(p * n, 1.0) if p is not None else None for p in p_values]


def compare_metric(
    metric_name: str,
    cli_values: list[float],
    mcp_values: list[float],
) -> ComparisonResult:
    """Full comparison of CLI vs MCP for a single metric."""
    cli_stats = descriptive_stats(cli_values)
    mcp_stats = descriptive_stats(mcp_values)

    mean_diff = cli_stats["mean"] - mcp_stats["mean"]
    d = cohens_d(cli_values, mcp_values)
    w_stat, p_val = wilcoxon_test(cli_values, mcp_values)
    ci_lo, ci_hi = confidence_interval_95(cli_values, mcp_values)

    # Determine winner (lower is better for tokens, latency, tool calls)
    if p_val is not None and p_val < 0.05:
        winner = "cli" if mean_diff < 0 else "mcp"
    else:
        winner = "tie"

    return ComparisonResult(
        metric=metric_name,
        cli_mean=cli_stats["mean"],
        cli_median=cli_stats["median"],
        cli_std=cli_stats["std"],
        cli_p25=cli_stats["p25"],
        cli_p75=cli_stats["p75"],
        cli_p95=cli_stats["p95"],
        mcp_mean=mcp_stats["mean"],
        mcp_median=mcp_stats["median"],
        mcp_std=mcp_stats["std"],
        mcp_p25=mcp_stats["p25"],
        mcp_p75=mcp_stats["p75"],
        mcp_p95=mcp_stats["p95"],
        mean_diff=mean_diff,
        ci_lower=ci_lo,
        ci_upper=ci_hi,
        wilcoxon_statistic=w_stat,
        p_value=p_val,
        cohens_d=d,
        winner=winner,
    )
