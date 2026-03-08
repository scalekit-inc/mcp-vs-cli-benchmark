"""Tests for MetricsCollector."""

import time
from datetime import timezone

from benchmark.metrics.collector import MetricsCollector
from benchmark.metrics.schemas import RunResult, ToolCallMetric


class TestRecordToolCall:
    """record_tool_call increments tool_call_count and stores the ToolCallMetric."""

    def test_single_tool_call(self):
        collector = MetricsCollector(run_id="r1", task_id="t1", modality="cli")
        assert collector.tool_call_count == 0

        collector.record_tool_call(
            tool_name="bash",
            tool_input={"command": "ls"},
            tool_output="file.txt",
            duration_ms=50.0,
            success=True,
        )

        assert collector.tool_call_count == 1
        assert len(collector.tool_calls) == 1
        metric = collector.tool_calls[0]
        assert isinstance(metric, ToolCallMetric)
        assert metric.tool_name == "bash"
        assert metric.tool_input == {"command": "ls"}
        assert metric.tool_output == "file.txt"
        assert metric.duration_ms == 50.0
        assert metric.success is True
        assert metric.error is None

    def test_multiple_tool_calls(self):
        collector = MetricsCollector(run_id="r1", task_id="t1", modality="mcp")

        for i in range(5):
            collector.record_tool_call(
                tool_name=f"tool_{i}",
                tool_input={"i": i},
                tool_output=f"out_{i}",
                duration_ms=float(i * 10),
                success=True,
            )

        assert collector.tool_call_count == 5
        assert [tc.tool_name for tc in collector.tool_calls] == [
            "tool_0", "tool_1", "tool_2", "tool_3", "tool_4"
        ]

    def test_tool_call_with_error(self):
        collector = MetricsCollector(run_id="r1", task_id="t1", modality="cli")
        collector.record_tool_call(
            tool_name="bash",
            tool_input={"command": "false"},
            tool_output="",
            duration_ms=5.0,
            success=False,
            error="exit code 1",
        )

        assert collector.tool_call_count == 1
        assert collector.tool_calls[0].success is False
        assert collector.tool_calls[0].error == "exit code 1"


class TestRecordApiResponse:
    """record_api_response accumulates input and output tokens across multiple calls."""

    def test_single_response(self):
        collector = MetricsCollector(run_id="r1", task_id="t1", modality="cli")
        collector.record_api_response(input_tokens=100, output_tokens=50)

        assert collector.total_input_tokens == 100
        assert collector.total_output_tokens == 50

    def test_accumulates_across_calls(self):
        collector = MetricsCollector(run_id="r1", task_id="t1", modality="mcp")

        collector.record_api_response(input_tokens=100, output_tokens=50)
        collector.record_api_response(input_tokens=200, output_tokens=75)
        collector.record_api_response(input_tokens=50, output_tokens=25)

        assert collector.total_input_tokens == 350
        assert collector.total_output_tokens == 150

    def test_starts_at_zero(self):
        collector = MetricsCollector(run_id="r1", task_id="t1", modality="cli")
        assert collector.total_input_tokens == 0
        assert collector.total_output_tokens == 0


class TestFinalize:
    """finalize() produces a valid RunResult with correct totals."""

    def test_produces_valid_run_result(self):
        collector = MetricsCollector(run_id="r1", task_id="t1", modality="cli")
        collector.record_tool_call(
            tool_name="bash",
            tool_input={"command": "echo hi"},
            tool_output="hi",
            duration_ms=30.0,
            success=True,
        )
        collector.record_api_response(input_tokens=500, output_tokens=200)

        result = collector.finalize(
            model="claude-opus-4-20250514",
            agent_output="Done.",
            task_completed=True,
            completion_score=1.0,
            is_cold_start=False,
        )

        assert isinstance(result, RunResult)
        assert result.run_id == "r1"
        assert result.task_id == "t1"
        assert result.modality == "cli"
        assert result.model == "claude-opus-4-20250514"
        assert result.input_tokens == 500
        assert result.output_tokens == 200
        assert result.total_tokens == 700
        assert result.tool_call_count == 1
        assert result.task_completed is True
        assert result.completion_score == 1.0
        assert result.agent_output == "Done."
        assert result.error is None
        assert result.is_cold_start is False

    def test_total_tokens_computed(self):
        collector = MetricsCollector(run_id="r2", task_id="t2", modality="mcp")
        collector.record_api_response(input_tokens=1000, output_tokens=300)
        collector.record_api_response(input_tokens=500, output_tokens=100)

        result = collector.finalize(
            model="m",
            agent_output="out",
            task_completed=False,
            completion_score=0.5,
            is_cold_start=True,
        )

        assert result.input_tokens == 1500
        assert result.output_tokens == 400
        assert result.total_tokens == 1900

    def test_wall_clock_seconds_positive(self):
        collector = MetricsCollector(run_id="r3", task_id="t3", modality="cli")
        # Small sleep to ensure non-zero elapsed time
        time.sleep(0.01)

        result = collector.finalize(
            model="m",
            agent_output="",
            task_completed=True,
            completion_score=0.0,
            is_cold_start=False,
        )

        assert result.wall_clock_seconds > 0.0

    def test_timestamp_is_utc(self):
        collector = MetricsCollector(run_id="r4", task_id="t4", modality="mcp")
        result = collector.finalize(
            model="m",
            agent_output="",
            task_completed=True,
            completion_score=1.0,
            is_cold_start=False,
        )

        assert result.timestamp.tzinfo == timezone.utc

    def test_finalize_with_error(self):
        collector = MetricsCollector(run_id="r5", task_id="t5", modality="cli")
        result = collector.finalize(
            model="m",
            agent_output="",
            task_completed=False,
            completion_score=0.0,
            is_cold_start=False,
            error="something went wrong",
        )

        assert result.error == "something went wrong"
        assert result.task_completed is False

    def test_finalize_includes_all_tool_calls(self):
        collector = MetricsCollector(run_id="r6", task_id="t6", modality="mcp")
        for i in range(3):
            collector.record_tool_call(
                tool_name=f"tool_{i}",
                tool_input={},
                tool_output="",
                duration_ms=1.0,
                success=True,
            )

        result = collector.finalize(
            model="m",
            agent_output="done",
            task_completed=True,
            completion_score=0.8,
            is_cold_start=True,
        )

        assert result.tool_call_count == 3
        assert len(result.tool_calls) == 3
        assert result.is_cold_start is True
