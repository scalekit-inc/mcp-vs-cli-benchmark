"""CLI entry point for the benchmark harness."""

import argparse
import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console

from benchmark.runner.config import BenchmarkConfig
from benchmark.runner.harness import BenchmarkHarness
from benchmark.tasks.registry import TaskRegistry

console = Console()


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(description="MCP vs CLI Benchmark")
    subparsers = parser.add_subparsers(dest="command")

    # Run command
    run_parser = subparsers.add_parser("run", help="Run benchmark suite")
    run_parser.add_argument("--service", nargs="+", default=["github"])
    run_parser.add_argument("--runs", type=int, default=30)
    run_parser.add_argument(
        "--model",
        default=os.environ.get("BENCHMARK_MODEL", "anthropic/claude-sonnet-4-20250514"),
    )
    run_parser.add_argument("--seed", type=int, default=None)
    run_parser.add_argument("--output", default="results/raw")
    run_parser.add_argument(
        "--task",
        default=None,
        help="Run only a specific task ID (e.g., github_01). Omit to run all.",
    )
    run_parser.add_argument(
        "--modality",
        default=None,
        choices=["cli", "mcp"],
        help="Run only one modality. Omit to run both.",
    )

    # Analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze results")
    analyze_parser.add_argument("--input", default="results/raw")

    args = parser.parse_args()

    if args.command == "run":
        _run(args)
    elif args.command == "analyze":
        console.print("[yellow]Analysis not yet implemented[/yellow]")
    else:
        parser.print_help()


def _run(args: argparse.Namespace) -> None:
    """Execute benchmark runs."""
    # Build config
    task_ids = None
    if args.task:
        # Single task mode: figure out which service it belongs to
        service = args.task.split("_")[0]
        task_ids = {service: [args.task]}
        services = [service]
    else:
        services = args.service

    config = BenchmarkConfig(
        runs_per_modality=args.runs,
        model=args.model,
        services=services,
        seed=args.seed,
        task_ids=task_ids,
    )

    # Load tasks
    tasks_dir = Path(__file__).parent.parent.parent / "tasks"
    if not tasks_dir.exists():
        # Fallback: try relative to cwd
        tasks_dir = Path("tasks")
    registry = TaskRegistry(tasks_dir)

    results_dir = Path(args.output)

    # Build schedule, optionally filter by modality
    schedule = config.build_schedule()
    if args.modality:
        schedule = [e for e in schedule if e.modality == args.modality]

    console.print("[bold]MCP vs CLI Benchmark[/bold]")
    console.print(f"  Model:     {config.model}")
    console.print(f"  Services:  {config.services}")
    console.print(f"  Runs/mod:  {config.runs_per_modality}")
    console.print(f"  Task:      {args.task or 'all'}")
    console.print(f"  Modality:  {args.modality or 'both'}")
    console.print(f"  Scheduled: {len(schedule)} runs")
    console.print(f"  Output:    {results_dir}")
    console.print()

    harness = BenchmarkHarness(config, registry, results_dir)
    results = asyncio.run(harness.run_schedule(schedule))

    console.print(f"\n[green]{len(results)} results saved to {results_dir}/[/green]")


if __name__ == "__main__":
    main()
