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
    run_parser.add_argument(
        "--clean",
        action="store_true",
        help="Clear previous results before running.",
    )

    # Analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze results")
    analyze_parser.add_argument("--input", default="results/raw")

    args = parser.parse_args()

    if args.command == "run":
        _run(args)
    elif args.command == "analyze":
        from benchmark.analysis.charts import generate_summary_dashboard, save_charts
        from benchmark.analysis.report import generate_markdown_report, load_results

        input_dir = Path(args.input)
        report = generate_markdown_report(input_dir)
        console.print(report)

        # Save markdown report
        report_path = input_dir.parent / "reports" / "report.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report)
        console.print(f"\n[green]Report saved to {report_path}[/green]")

        # Generate charts
        results = load_results(input_dir)
        if results:
            charts_dir = input_dir.parent / "charts"
            paths = save_charts(results, charts_dir)
            for p in paths:
                console.print(f"  [dim]Chart: {p}[/dim]")
            dashboard = generate_summary_dashboard(results, charts_dir)
            console.print(f"[green]Dashboard saved to {dashboard}[/green]")
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

    # Clear previous results if --clean
    if args.clean and results_dir.exists():
        removed = list(results_dir.glob("*.json"))
        for f in removed:
            f.unlink()
        if removed:
            console.print(f"[yellow]Cleaned {len(removed)} previous results from {results_dir}/[/yellow]\n")

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
