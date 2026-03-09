"""Tests for the statistical analysis module."""

import pytest

from benchmark.analysis.stats import (
    ComparisonResult,
    bonferroni_correct,
    cohens_d,
    compare_metric,
    confidence_interval_95,
    descriptive_stats,
    wilcoxon_test,
)


class TestDescriptiveStats:
    def test_descriptive_stats(self):
        values = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
        result = descriptive_stats(values)

        assert result["mean"] == pytest.approx(5.5)
        assert result["median"] == pytest.approx(5.5)
        assert result["std"] == pytest.approx(3.0276, rel=1e-3)
        assert result["min"] == pytest.approx(1.0)
        assert result["max"] == pytest.approx(10.0)
        assert result["p25"] == pytest.approx(3.25)
        assert result["p75"] == pytest.approx(7.75)
        assert result["p95"] == pytest.approx(9.55)

    def test_descriptive_stats_single_value(self):
        result = descriptive_stats([42.0])
        assert result["mean"] == pytest.approx(42.0)
        assert result["std"] == pytest.approx(0.0)


class TestCohensD:
    def test_cohens_d_identical(self):
        group = [5.0, 5.0, 5.0, 5.0, 5.0]
        d = cohens_d(group, group)
        assert d == pytest.approx(0.0)

    def test_cohens_d_different(self):
        group1 = [10.0, 11.0, 12.0, 13.0, 14.0]
        group2 = [1.0, 2.0, 3.0, 4.0, 5.0]
        d = cohens_d(group1, group2)
        # Large positive effect size (group1 >> group2)
        assert d > 2.0

    def test_cohens_d_small_sample(self):
        d = cohens_d([1.0], [2.0])
        assert d == 0.0


class TestWilcoxon:
    def test_wilcoxon_identical(self):
        values = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
        stat, p = wilcoxon_test(values, values)
        # All diffs zero → returns None
        assert stat is None
        assert p is None

    def test_wilcoxon_different(self):
        group1 = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0]
        group2 = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
        stat, p = wilcoxon_test(group1, group2)
        assert stat is not None
        assert p is not None
        assert p < 0.05  # Should be significant

    def test_wilcoxon_too_few_samples(self):
        stat, p = wilcoxon_test([1.0, 2.0], [3.0, 4.0])
        assert stat is None
        assert p is None

    def test_wilcoxon_unequal_lengths(self):
        stat, p = wilcoxon_test([1.0, 2.0, 3.0], [4.0, 5.0])
        assert stat is None
        assert p is None


class TestConfidenceInterval:
    def test_confidence_interval(self):
        # group1 is consistently 10 higher than group2
        group1 = [110.0, 120.0, 130.0, 140.0, 150.0, 160.0]
        group2 = [100.0, 110.0, 120.0, 130.0, 140.0, 150.0]
        ci_lo, ci_hi = confidence_interval_95(group1, group2)
        # True mean diff is 10.0; CI should contain it
        assert ci_lo <= 10.0 <= ci_hi

    def test_confidence_interval_single_pair(self):
        ci_lo, ci_hi = confidence_interval_95([5.0], [3.0])
        assert ci_lo == 0.0
        assert ci_hi == 0.0


class TestBonferroni:
    def test_bonferroni_correction(self):
        p_values = [0.01, 0.04, None, 0.03]
        corrected = bonferroni_correct(p_values)
        # 3 non-None p-values, so multiply by 3
        assert corrected[0] == pytest.approx(0.03)
        assert corrected[1] == pytest.approx(0.12)
        assert corrected[2] is None
        assert corrected[3] == pytest.approx(0.09)

    def test_bonferroni_caps_at_one(self):
        corrected = bonferroni_correct([0.5, 0.6])
        assert corrected[0] == pytest.approx(1.0)
        assert corrected[1] == pytest.approx(1.0)

    def test_bonferroni_custom_n(self):
        corrected = bonferroni_correct([0.01], num_comparisons=10)
        assert corrected[0] == pytest.approx(0.1)


class TestCompareMetric:
    def test_compare_metric_returns_winner(self):
        # CLI values are clearly lower → CLI should win (lower is better)
        cli_values = [10.0, 11.0, 12.0, 13.0, 14.0, 15.0]
        mcp_values = [100.0, 110.0, 120.0, 130.0, 140.0, 150.0]
        result = compare_metric("total_tokens", cli_values, mcp_values)

        assert isinstance(result, ComparisonResult)
        assert result.metric == "total_tokens"
        assert result.cli_mean < result.mcp_mean
        assert result.mean_diff < 0  # cli - mcp is negative (CLI lower)
        assert result.winner == "cli"  # negative diff + significant → cli wins
        assert result.cohens_d < 0  # large negative effect

    def test_compare_metric_tie_when_similar(self):
        cli_values = [10.0, 11.0, 10.5, 10.2, 10.8, 10.3]
        mcp_values = [10.1, 10.9, 10.4, 10.3, 10.7, 10.2]
        result = compare_metric("wall_clock", cli_values, mcp_values)
        # Very similar values → should be a tie (p > 0.05)
        assert result.winner == "tie"
