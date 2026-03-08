"""MetricsCollector for tracking tokens, tool calls, and timing during benchmark runs."""

import time
from datetime import datetime, timezone

from benchmark.metrics.schemas import RunResult, ToolCallMetric


class MetricsCollector:
    """Collects metrics during a single benchmark run."""

    def __init__(self, run_id: str, task_id: str, modality: str) -> None:
        self.run_id = run_id
        self.task_id = task_id
        self.modality = modality
        self.tool_calls: list[ToolCallMetric] = []
        self.total_input_tokens: int = 0
        self.total_output_tokens: int = 0
        self._start_time: float = time.monotonic()

    @property
    def tool_call_count(self) -> int:
        return len(self.tool_calls)

    def record_tool_call(
        self,
        tool_name: str,
        tool_input: dict,
        tool_output: str,
        duration_ms: float,
        success: bool,
        error: str | None = None,
    ) -> None:
        """Record a single tool call with its metrics."""
        self.tool_calls.append(
            ToolCallMetric(
                tool_name=tool_name,
                tool_input=tool_input,
                tool_output=tool_output,
                duration_ms=duration_ms,
                success=success,
                error=error,
            )
        )

    def record_api_response(self, input_tokens: int, output_tokens: int) -> None:
        """Accumulate token counts from an API response."""
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens

    def finalize(
        self,
        model: str,
        agent_output: str,
        task_completed: bool,
        completion_score: float,
        is_cold_start: bool,
        error: str | None = None,
    ) -> RunResult:
        """Produce the final RunResult with all accumulated metrics."""
        elapsed = time.monotonic() - self._start_time
        return RunResult(
            run_id=self.run_id,
            task_id=self.task_id,
            modality=self.modality,
            model=model,
            timestamp=datetime.now(timezone.utc),
            input_tokens=self.total_input_tokens,
            output_tokens=self.total_output_tokens,
            total_tokens=self.total_input_tokens + self.total_output_tokens,
            tool_calls=self.tool_calls,
            tool_call_count=self.tool_call_count,
            wall_clock_seconds=elapsed,
            task_completed=task_completed,
            completion_score=completion_score,
            agent_output=agent_output,
            error=error,
            is_cold_start=is_cold_start,
        )
