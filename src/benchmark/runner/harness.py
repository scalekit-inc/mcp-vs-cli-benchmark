"""Benchmark harness — orchestrates scheduled runs."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from benchmark.runner.config import BenchmarkConfig, ScheduleEntry
from benchmark.tasks.registry import TaskRegistry


class BenchmarkHarness:
    """Runs scheduled benchmark entries and collects results."""

    def __init__(
        self, config: BenchmarkConfig, registry: TaskRegistry, results_dir: Path
    ) -> None:
        self._config = config
        self._registry = registry
        self._results_dir = results_dir

    async def run_schedule(self, schedule: list[ScheduleEntry]) -> list[dict[str, Any]]:
        """Execute all scheduled runs. Skeleton — skips tasks not found in registry."""
        results: list[dict[str, Any]] = []
        for entry in schedule:
            task = self._registry.get_task(entry.task_id)
            if task is None:
                continue
            # TODO: execute task via CLI or MCP agent
            results.append({"run_id": entry.run_id, "task_id": entry.task_id, "status": "skipped"})
        return results

    def save_all_results(self, results: list[dict[str, Any]]) -> None:
        """Persist results to disk."""
        self._results_dir.mkdir(parents=True, exist_ok=True)
        # TODO: write results as JSON
