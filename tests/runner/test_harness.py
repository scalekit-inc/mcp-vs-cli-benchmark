"""Tests for BenchmarkConfig scheduler and BenchmarkHarness."""

from benchmark.runner.config import BenchmarkConfig


def test_scheduler_alternates_modalities():
    """Every pair of consecutive entries should be {cli, mcp}."""
    config = BenchmarkConfig(
        runs_per_modality=5,
        services=["github"],
        task_ids={"github": ["github_01", "github_02"]},
        seed=42,
    )
    schedule = config.build_schedule()

    # Entries come in pairs: one cli, one mcp for the same task
    for i in range(0, len(schedule), 2):
        pair = {schedule[i].modality, schedule[i + 1].modality}
        assert pair == {"cli", "mcp"}, (
            f"Entries at index {i},{i+1} should be {{cli, mcp}}, got {pair}"
        )


def test_scheduler_randomizes_task_order():
    """With a seed, task IDs should vary across runs (not always same order)."""
    config = BenchmarkConfig(
        runs_per_modality=10,
        services=["github"],
        task_ids={"github": [f"github_{i:02d}" for i in range(1, 6)]},
        seed=123,
    )
    schedule = config.build_schedule()

    # Collect the task_id ordering per round (each round has 5 tasks x 2 modalities = 10 entries)
    tasks_per_round: list[list[str]] = []
    entries_per_round = 5 * 2  # 5 tasks, 2 modalities each
    for round_start in range(0, len(schedule), entries_per_round):
        round_entries = schedule[round_start : round_start + entries_per_round]
        # Take just the cli entries to get the task order
        cli_tasks = [e.task_id for e in round_entries if e.modality == "cli"]
        tasks_per_round.append(cli_tasks)

    # Not all rounds should have the same order (randomization should shuffle)
    assert len(tasks_per_round) >= 2
    orders_differ = any(
        tasks_per_round[i] != tasks_per_round[0] for i in range(1, len(tasks_per_round))
    )
    assert orders_differ, "Task order should vary across rounds due to randomization"


def test_config_marks_cold_starts():
    """First N runs per modality should be marked as cold starts."""
    cold_start_runs = 3
    config = BenchmarkConfig(
        runs_per_modality=5,
        services=["github"],
        task_ids={"github": ["github_01", "github_02"]},
        cold_start_runs=cold_start_runs,
        seed=42,
    )
    schedule = config.build_schedule()

    cli_entries = [e for e in schedule if e.modality == "cli"]
    mcp_entries = [e for e in schedule if e.modality == "mcp"]

    # First cold_start_runs entries per modality should be cold
    for entries in [cli_entries, mcp_entries]:
        for i, entry in enumerate(entries):
            if i < cold_start_runs:
                assert entry.is_cold_start, (
                    f"Entry {i} (run_number={entry.run_number}) should be cold start"
                )
            else:
                assert not entry.is_cold_start, (
                    f"Entry {i} (run_number={entry.run_number}) should NOT be cold start"
                )


def test_schedule_total_count():
    """5 tasks x 30 runs x 2 modalities = 300 entries for github."""
    config = BenchmarkConfig(
        runs_per_modality=30,
        services=["github"],
        task_ids={"github": [f"github_{i:02d}" for i in range(1, 6)]},
        seed=1,
    )
    schedule = config.build_schedule()
    assert len(schedule) == 5 * 30 * 2  # 300
