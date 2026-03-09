"""Tests for the charts visualization module."""

import uuid
from datetime import datetime, timezone
from pathlib import Path

import plotly.graph_objects as go
import pytest

from benchmark.analysis.charts import (
    completion_rate_chart,
    generate_summary_dashboard,
    latency_box_plot,
    save_charts,
    token_comparison_chart,
    tool_calls_chart,
)
from benchmark.metrics.schemas import RunResult


def _make_run(
    task_id: str = "task-1",
    modality: str = "cli",
    total_tokens: int = 1000,
    tool_call_count: int = 5,
    wall_clock_seconds: float = 10.0,
    task_completed: bool = True,
) -> RunResult:
    """Create a synthetic RunResult for testing."""
    return RunResult(
        run_id=str(uuid.uuid4()),
        task_id=task_id,
        modality=modality,
        model="test-model",
        timestamp=datetime.now(timezone.utc),
        input_tokens=total_tokens // 2,
        output_tokens=total_tokens // 2,
        total_tokens=total_tokens,
        tool_calls=[],
        tool_call_count=tool_call_count,
        wall_clock_seconds=wall_clock_seconds,
        task_completed=task_completed,
        completion_score=1.0 if task_completed else 0.0,
        agent_output="test output",
        is_cold_start=False,
    )


@pytest.fixture
def multi_task_results() -> list[RunResult]:
    """Multiple runs across two tasks and both modalities."""
    results = []
    for task_id in ["task-1", "task-2"]:
        for i in range(3):
            results.append(_make_run(
                task_id=task_id,
                modality="cli",
                total_tokens=1000 + i * 100,
                tool_call_count=5 + i,
                wall_clock_seconds=10.0 + i,
                task_completed=True,
            ))
            results.append(_make_run(
                task_id=task_id,
                modality="mcp",
                total_tokens=1200 + i * 100,
                tool_call_count=3 + i,
                wall_clock_seconds=8.0 + i,
                task_completed=i < 2,  # one failure per task
            ))
    return results


@pytest.fixture
def single_run_results() -> list[RunResult]:
    """Edge case: single run per modality."""
    return [
        _make_run(task_id="solo", modality="cli", total_tokens=500),
        _make_run(task_id="solo", modality="mcp", total_tokens=700),
    ]


@pytest.fixture
def single_modality_results() -> list[RunResult]:
    """Edge case: only one modality present for a task."""
    return [
        _make_run(task_id="only-cli", modality="cli"),
        _make_run(task_id="only-cli", modality="cli"),
    ]


class TestTokenComparisonChart:
    def test_returns_figure(self, multi_task_results: list[RunResult]) -> None:
        fig = token_comparison_chart(multi_task_results)
        assert isinstance(fig, go.Figure)

    def test_has_traces_for_present_modalities(self, multi_task_results: list[RunResult]) -> None:
        fig = token_comparison_chart(multi_task_results)
        trace_names = {t.name for t in fig.data}
        assert "CLI" in trace_names
        assert "MCP" in trace_names

    def test_single_run(self, single_run_results: list[RunResult]) -> None:
        fig = token_comparison_chart(single_run_results)
        assert isinstance(fig, go.Figure)
        assert len(fig.data) >= 1

    def test_missing_modality(self, single_modality_results: list[RunResult]) -> None:
        fig = token_comparison_chart(single_modality_results)
        assert isinstance(fig, go.Figure)
        # Only CLI trace should be present (no MCP data)
        assert len(fig.data) == 1
        assert fig.data[0].name == "CLI"


class TestLatencyBoxPlot:
    def test_returns_figure(self, multi_task_results: list[RunResult]) -> None:
        fig = latency_box_plot(multi_task_results)
        assert isinstance(fig, go.Figure)

    def test_has_two_traces(self, multi_task_results: list[RunResult]) -> None:
        fig = latency_box_plot(multi_task_results)
        assert len(fig.data) == 2

    def test_single_run(self, single_run_results: list[RunResult]) -> None:
        fig = latency_box_plot(single_run_results)
        assert isinstance(fig, go.Figure)


class TestToolCallsChart:
    def test_returns_figure(self, multi_task_results: list[RunResult]) -> None:
        fig = tool_calls_chart(multi_task_results)
        assert isinstance(fig, go.Figure)

    def test_has_two_traces(self, multi_task_results: list[RunResult]) -> None:
        fig = tool_calls_chart(multi_task_results)
        assert len(fig.data) == 2
        assert fig.data[0].name == "CLI"
        assert fig.data[1].name == "MCP"

    def test_missing_modality(self, single_modality_results: list[RunResult]) -> None:
        fig = tool_calls_chart(single_modality_results)
        assert isinstance(fig, go.Figure)


class TestCompletionRateChart:
    def test_returns_figure(self, multi_task_results: list[RunResult]) -> None:
        fig = completion_rate_chart(multi_task_results)
        assert isinstance(fig, go.Figure)

    def test_rates_are_percentages(self, multi_task_results: list[RunResult]) -> None:
        fig = completion_rate_chart(multi_task_results)
        # CLI: all 3 completed = 100%, MCP: 2/3 completed ~66.7%
        cli_rates = list(fig.data[0].y)
        mcp_rates = list(fig.data[1].y)
        assert all(0 <= r <= 100 for r in cli_rates)
        assert all(0 <= r <= 100 for r in mcp_rates)
        # CLI should be 100% for both tasks
        assert cli_rates[0] == pytest.approx(100.0)
        # MCP should be ~66.7% for both tasks
        assert mcp_rates[0] == pytest.approx(66.666, abs=0.1)

    def test_missing_modality(self, single_modality_results: list[RunResult]) -> None:
        fig = completion_rate_chart(single_modality_results)
        assert isinstance(fig, go.Figure)


class TestSaveCharts:
    def test_creates_html_files(
        self, multi_task_results: list[RunResult], tmp_path: Path
    ) -> None:
        paths = save_charts(multi_task_results, tmp_path / "charts")
        assert len(paths) == 4
        for p in paths:
            assert p.exists()
            assert p.suffix == ".html"
            assert p.stat().st_size > 0

    def test_creates_output_dir(
        self, multi_task_results: list[RunResult], tmp_path: Path
    ) -> None:
        out = tmp_path / "nested" / "dir"
        assert not out.exists()
        save_charts(multi_task_results, out)
        assert out.exists()

    def test_single_run(
        self, single_run_results: list[RunResult], tmp_path: Path
    ) -> None:
        paths = save_charts(single_run_results, tmp_path / "single")
        assert len(paths) == 4
        for p in paths:
            assert p.exists()


class TestGenerateSummaryDashboard:
    def test_creates_dashboard(
        self, multi_task_results: list[RunResult], tmp_path: Path
    ) -> None:
        path = generate_summary_dashboard(multi_task_results, tmp_path)
        assert path.exists()
        assert path.name == "dashboard.html"
        content = path.read_text()
        assert "plotly" in content.lower()
        assert "MCP vs CLI Benchmark Dashboard" in content

    def test_creates_output_dir(
        self, multi_task_results: list[RunResult], tmp_path: Path
    ) -> None:
        out = tmp_path / "new_dir"
        generate_summary_dashboard(multi_task_results, out)
        assert out.exists()

    def test_single_run(
        self, single_run_results: list[RunResult], tmp_path: Path
    ) -> None:
        path = generate_summary_dashboard(single_run_results, tmp_path)
        assert path.exists()
