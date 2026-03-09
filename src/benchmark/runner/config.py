import random
import uuid
from pydantic import BaseModel


class ScheduleEntry(BaseModel):
    """A single scheduled run in the benchmark."""
    run_id: str
    task_id: str
    service: str
    modality: str  # "cli", "mcp", "gateway", or "cli_skilled"
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
    model: str = "anthropic/claude-sonnet-4-20250514"
    judge_model: str = "anthropic/claude-opus-4-20250514"
    services: list[str] = ["github"]
    cold_start_runs: int = 3
    seed: int | None = None
    task_ids: dict[str, list[str]] | None = None
    skills: bool = False
    modalities: list[str] = ["cli", "mcp"]

    def build_schedule(self) -> list[ScheduleEntry]:
        """Build schedule with entries for each configured modality.

        Entries are grouped per task: one entry per modality, interleaved.
        Task order within each round is randomized via the seed.
        """
        rng = random.Random(self.seed)
        task_map = self.task_ids or DEFAULT_TASK_IDS
        entries: list[ScheduleEntry] = []

        # Resolve effective modalities: if skills is set, add "cli_skilled" alongside "cli"
        effective_modalities = list(self.modalities)
        if self.skills and "cli_skilled" not in effective_modalities:
            # Insert cli_skilled right after cli
            idx = effective_modalities.index("cli") + 1 if "cli" in effective_modalities else 0
            effective_modalities.insert(idx, "cli_skilled")
        modality_counts: dict[str, int] = {m: 0 for m in effective_modalities}

        for run_num in range(1, self.runs_per_modality + 1):
            tasks_this_round: list[tuple[str, str]] = []
            for service in self.services:
                service_tasks = task_map.get(service, [])
                for tid in service_tasks:
                    tasks_this_round.append((service, tid))
            rng.shuffle(tasks_this_round)

            for service, task_id in tasks_this_round:
                for modality in effective_modalities:
                    modality_counts[modality] += 1
                    entries.append(ScheduleEntry(
                        run_id=str(uuid.uuid4()),
                        task_id=task_id, service=service, modality=modality,
                        is_cold_start=modality_counts[modality] <= self.cold_start_runs,
                        run_number=modality_counts[modality],
                    ))

        return entries
