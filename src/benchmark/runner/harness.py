"""Benchmark harness — orchestrates scheduled runs with real agents."""

import json
from pathlib import Path

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from benchmark.agents.cli_agent import CliAgent
from benchmark.agents.mcp_agent import McpAgent
from benchmark.metrics.schemas import RunResult
from benchmark.metrics.verifier import verify_output
from benchmark.runner.config import BenchmarkConfig, ScheduleEntry
from benchmark.runner.mcp_manager import mcp_session
from benchmark.tasks.registry import TaskRegistry
from benchmark.tasks.schema import TaskDefinition

console = Console()


class BenchmarkHarness:
    """Runs scheduled benchmark entries via CLI and MCP agents."""

    def __init__(
        self,
        config: BenchmarkConfig,
        registry: TaskRegistry,
        results_dir: Path,
    ) -> None:
        self.config = config
        self.registry = registry
        self.results_dir = results_dir
        self.results_dir.mkdir(parents=True, exist_ok=True)

    async def run_schedule(self, schedule: list[ScheduleEntry]) -> list[RunResult]:
        """Execute all scheduled runs, alternating CLI/MCP."""
        results: list[RunResult] = []
        total = len(schedule)
        completed = 0
        failed = 0

        for i, entry in enumerate(schedule, 1):
            task_def = self.registry.get_task(entry.task_id)
            if task_def is None:
                console.print(f"  [yellow]Skip: unknown task {entry.task_id}[/yellow]")
                continue

            label = (
                f"[{'cyan' if entry.modality == 'cli' else 'magenta'}]"
                f"{entry.modality.upper()}[/] {entry.task_id} "
                f"(#{entry.run_number}, {'cold' if entry.is_cold_start else 'warm'})"
            )

            try:
                with console.status(f"  {label} [{i}/{total}]"):
                    result = await self._run_single(entry, task_def)
                results.append(result)
                self._save_result(result)

                # Quick verification
                v = verify_output(result.agent_output, task_def.verification)
                status = "[green]PASS[/green]" if v.passed else f"[red]FAIL ({v.score:.0%})[/red]"
                console.print(
                    f"  {label} → {result.total_tokens} tok, "
                    f"{result.tool_call_count} calls, "
                    f"{result.wall_clock_seconds:.1f}s, "
                    f"{status}"
                )
                completed += 1

            except Exception as e:
                console.print(f"  {label} → [red]ERROR: {e}[/red]")
                failed += 1

        console.print(
            f"\n[bold]Done:[/bold] {completed} completed, {failed} failed, "
            f"{total - completed - failed} skipped"
        )
        return results

    async def _run_single(self, entry: ScheduleEntry, task_def: TaskDefinition) -> RunResult:
        """Run a single benchmark entry via the appropriate agent."""
        if entry.modality == "cli":
            return await self._run_cli(entry, task_def)
        elif entry.modality == "mcp":
            return await self._run_mcp(entry, task_def)
        else:
            raise ValueError(f"Unknown modality: {entry.modality}")

    async def _run_cli(self, entry: ScheduleEntry, task_def: TaskDefinition) -> RunResult:
        """Run a task via CLI agent."""
        agent = CliAgent(model=self.config.model)
        return await agent.run(
            task=task_def,
            run_id=entry.run_id,
            modality="cli",
            is_cold_start=entry.is_cold_start,
        )

    async def _run_mcp(self, entry: ScheduleEntry, task_def: TaskDefinition) -> RunResult:
        """Run a task via MCP agent with a fresh server session."""
        async with mcp_session(entry.service) as session:
            agent = await McpAgent.from_session(
                model=self.config.model,
                session=session,
            )
            return await agent.run(
                task=task_def,
                run_id=entry.run_id,
                modality="mcp",
                is_cold_start=entry.is_cold_start,
            )

    def _save_result(self, result: RunResult) -> None:
        """Save a single run result as JSON."""
        path = self.results_dir / f"{result.run_id}.json"
        path.write_text(result.model_dump_json(indent=2))

    def save_all_results(self, results: list[RunResult]) -> None:
        """Save all results (redundant if _save_result called per-run, but useful for re-saves)."""
        for result in results:
            self._save_result(result)
