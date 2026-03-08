"""Tests for Pydantic metric schemas."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from benchmark.metrics.schemas import (
    JudgeVerdict,
    RunResult,
    TaskComparison,
    ToolCallMetric,
)


class TestToolCallMetric:
    """Tests for ToolCallMetric schema."""

    def test_roundtrip(self):
        """Create -> model_dump -> model_validate produces identical object."""
        metric = ToolCallMetric(
            tool_name="read_file",
            tool_input={"path": "/tmp/test.txt"},
            tool_output="file contents here",
            duration_ms=123.45,
            success=True,
            error=None,
        )
        dumped = metric.model_dump()
        restored = ToolCallMetric.model_validate(dumped)
        assert restored == metric

    def test_error_field_optional(self):
        """Error field defaults to None."""
        metric = ToolCallMetric(
            tool_name="bash",
            tool_input={"command": "ls"},
            tool_output="output",
            duration_ms=50.0,
            success=True,
        )
        assert metric.error is None

    def test_error_field_populated(self):
        """Error field can hold a string."""
        metric = ToolCallMetric(
            tool_name="bash",
            tool_input={"command": "false"},
            tool_output="",
            duration_ms=10.0,
            success=False,
            error="command failed with exit code 1",
        )
        assert metric.error == "command failed with exit code 1"


class TestRunResult:
    """Tests for RunResult schema."""

    @pytest.fixture
    def sample_run(self) -> RunResult:
        return RunResult(
            run_id="run-001",
            task_id="task-001",
            modality="cli",
            model="claude-opus-4-20250514",
            timestamp=datetime(2026, 3, 8, 12, 0, 0, tzinfo=timezone.utc),
            input_tokens=1500,
            output_tokens=500,
            total_tokens=2000,
            tool_calls=[
                ToolCallMetric(
                    tool_name="bash",
                    tool_input={"command": "ls"},
                    tool_output="file1.txt",
                    duration_ms=80.0,
                    success=True,
                )
            ],
            tool_call_count=1,
            wall_clock_seconds=5.2,
            task_completed=True,
            completion_score=0.95,
            agent_output="Task done.",
            error=None,
            is_cold_start=False,
        )

    def test_all_fields(self, sample_run: RunResult):
        """RunResult stores all expected fields."""
        assert sample_run.run_id == "run-001"
        assert sample_run.modality == "cli"
        assert sample_run.completion_score == 0.95
        assert len(sample_run.tool_calls) == 1
        assert sample_run.is_cold_start is False

    def test_json_roundtrip(self, sample_run: RunResult):
        """Serialize to JSON and back produces identical object."""
        json_str = sample_run.model_dump_json()
        restored = RunResult.model_validate_json(json_str)
        assert restored == sample_run

    def test_invalid_modality_rejected(self):
        """Modality must be 'cli' or 'mcp'."""
        with pytest.raises(ValidationError):
            RunResult(
                run_id="run-bad",
                task_id="task-001",
                modality="rest",  # type: ignore[arg-type]
                model="claude-opus-4-20250514",
                timestamp=datetime.now(tz=timezone.utc),
                input_tokens=0,
                output_tokens=0,
                total_tokens=0,
                tool_calls=[],
                tool_call_count=0,
                wall_clock_seconds=0.0,
                task_completed=False,
                completion_score=0.0,
                agent_output="",
                is_cold_start=False,
            )

    def test_completion_score_bounds(self):
        """completion_score must be between 0.0 and 1.0."""
        base = dict(
            run_id="run-x",
            task_id="task-x",
            modality="mcp",
            model="m",
            timestamp=datetime.now(tz=timezone.utc),
            input_tokens=0,
            output_tokens=0,
            total_tokens=0,
            tool_calls=[],
            tool_call_count=0,
            wall_clock_seconds=0.0,
            task_completed=False,
            agent_output="",
            is_cold_start=False,
        )
        with pytest.raises(ValidationError):
            RunResult(**base, completion_score=-0.1)
        with pytest.raises(ValidationError):
            RunResult(**base, completion_score=1.1)


class TestJudgeVerdict:
    """Tests for JudgeVerdict schema."""

    def test_valid_verdict(self):
        verdict = JudgeVerdict(
            run_id="run-001",
            task_id="task-001",
            quality_score=4,
            rationale="Good output with minor issues.",
            judge_model="claude-opus-4-20250514",
            attempt=1,
        )
        assert verdict.quality_score == 4

    def test_quality_score_too_low(self):
        """quality_score below 1 is rejected."""
        with pytest.raises(ValidationError):
            JudgeVerdict(
                run_id="run-001",
                task_id="task-001",
                quality_score=0,
                rationale="Bad",
                judge_model="m",
                attempt=1,
            )

    def test_quality_score_too_high(self):
        """quality_score above 5 is rejected."""
        with pytest.raises(ValidationError):
            JudgeVerdict(
                run_id="run-001",
                task_id="task-001",
                quality_score=6,
                rationale="Great",
                judge_model="m",
                attempt=1,
            )

    def test_attempt_bounds(self):
        """attempt must be between 1 and 3."""
        with pytest.raises(ValidationError):
            JudgeVerdict(
                run_id="r",
                task_id="t",
                quality_score=3,
                rationale="ok",
                judge_model="m",
                attempt=0,
            )
        with pytest.raises(ValidationError):
            JudgeVerdict(
                run_id="r",
                task_id="t",
                quality_score=3,
                rationale="ok",
                judge_model="m",
                attempt=4,
            )


class TestTaskComparison:
    """Tests for TaskComparison schema."""

    def test_empty_runs(self):
        comp = TaskComparison(
            task_id="task-001",
            service="github",
            cli_runs=[],
            mcp_runs=[],
        )
        assert comp.cli_verdicts == []
        assert comp.mcp_verdicts == []
