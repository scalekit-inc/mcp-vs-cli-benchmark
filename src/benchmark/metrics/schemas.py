"""Pydantic schemas for benchmark metrics: runs, tool calls, and judge verdicts."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ToolCallMetric(BaseModel):
    """Metrics for a single tool invocation within a run."""

    tool_name: str
    tool_input: dict
    tool_output: str
    duration_ms: float
    success: bool
    error: str | None = None


class RunResult(BaseModel):
    """Complete result of a single benchmark run (one agent + one task)."""

    run_id: str
    task_id: str
    task_name: str = ""
    modality: Literal["cli", "mcp", "gateway", "cli_skilled"]
    model: str
    timestamp: datetime
    input_tokens: int
    output_tokens: int
    total_tokens: int
    tool_calls: list[ToolCallMetric]
    tool_call_count: int
    wall_clock_seconds: float
    task_completed: bool
    completion_score: float = Field(ge=0.0, le=1.0)
    agent_output: str
    error: str | None = None
    is_cold_start: bool


class JudgeVerdict(BaseModel):
    """LLM-as-judge evaluation of a run's output quality."""

    run_id: str
    task_id: str
    quality_score: int = Field(ge=1, le=5)
    rationale: str
    judge_model: str
    attempt: int = Field(ge=1, le=3)


class TaskComparison(BaseModel):
    """Aggregated comparison of CLI vs MCP for a single task."""

    task_id: str
    service: str
    cli_runs: list[RunResult]
    mcp_runs: list[RunResult]
    cli_verdicts: list[JudgeVerdict] = []
    mcp_verdicts: list[JudgeVerdict] = []
