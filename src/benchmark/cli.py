"""CLI entry point for the benchmark harness."""
import argparse
import asyncio
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

    run_parser = subparsers.add_parser("run", help="Run benchmark suite")
    run_parser.add_argument("--service", nargs="+", default=["github"])
    run_parser.add_argument("--runs", type=int, default=30)
    run_parser.add_argument("--model", default="claude-sonnet-4-20250514")
    run_parser.add_argument("--seed", type=int, default=None)
    run_parser.add_argument("--output", default="results/raw")

    analyze_parser = subparsers.add_parser("analyze", help="Analyze results")
    analyze_parser.add_argument("--input", default="results/raw")

    args = parser.parse_args()

    if args.command == "run":
        config = BenchmarkConfig(
            runs_per_modality=args.runs,
            model=args.model,
            services=args.service,
            seed=args.seed,
        )
        tasks_dir = Path(__file__).parent.parent.parent / "tasks"
        registry = TaskRegistry(tasks_dir)
        results_dir = Path(args.output)

        harness = BenchmarkHarness(config, registry, results_dir)
        schedule = config.build_schedule()

        console.print("[bold]MCP vs CLI Benchmark[/]")
        console.print(f"Services: {config.services}")
        console.print(f"Runs per modality: {config.runs_per_modality}")
        console.print(f"Total scheduled runs: {len(schedule)}")
        console.print()

        results = asyncio.run(harness.run_schedule(schedule))
        harness.save_all_results(results)
        console.print(f"\n[green]Done. {len(results)} results saved to {results_dir}[/]")

    elif args.command == "analyze":
        console.print("[yellow]Analysis not yet implemented[/]")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
