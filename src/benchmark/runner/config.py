import random
import uuid
from pydantic import BaseModel


class ScheduleEntry(BaseModel):
    """A single scheduled run in the benchmark."""
    run_id: str
    task_id: str
    service: str
    modality: str  # "cli" or "mcp"
    is_cold_start: bool
    run_number: int  # 1-based index within this modality


DEFAULT_TASK_IDS: dict[str, list[str]] = {
    "github": [f"github_{i:02d}" for i in range(1, 6)],
    "google": [f"google_{i:02d}" for i in range(1, 6)],
    "postgres": [f"postgres_{i:02d}" for i in range(1, 6)],
}


class BenchmarkConfig(BaseModel):
    """Configuration for a benchmark run suite."""
    runs_per_modality: int = 30
    model: str = "claude-sonnet-4-20250514"
    judge_model: str = "claude-opus-4-20250514"
    services: list[str] = ["github"]
    cold_start_runs: int = 3
    seed: int | None = None
    task_ids: dict[str, list[str]] | None = None

    def build_schedule(self) -> list[ScheduleEntry]:
        """Build alternating CLI/MCP schedule with randomized task order."""
        rng = random.Random(self.seed)
        task_map = self.task_ids or DEFAULT_TASK_IDS
        entries: list[ScheduleEntry] = []
        cli_count = 0
        mcp_count = 0

        for run_num in range(1, self.runs_per_modality + 1):
            tasks_this_round: list[tuple[str, str]] = []
            for service in self.services:
                service_tasks = task_map.get(service, [])
                for tid in service_tasks:
                    tasks_this_round.append((service, tid))
            rng.shuffle(tasks_this_round)

            for service, task_id in tasks_this_round:
                cli_count += 1
                entries.append(ScheduleEntry(
                    run_id=str(uuid.uuid4()),
                    task_id=task_id, service=service, modality="cli",
                    is_cold_start=cli_count <= self.cold_start_runs,
                    run_number=cli_count,
                ))
                mcp_count += 1
                entries.append(ScheduleEntry(
                    run_id=str(uuid.uuid4()),
                    task_id=task_id, service=service, modality="mcp",
                    is_cold_start=mcp_count <= self.cold_start_runs,
                    run_number=mcp_count,
                ))

        return entries
