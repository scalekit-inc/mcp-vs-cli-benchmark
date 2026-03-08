#!/usr/bin/env python3
"""Integration test: run one real CLI task with a real LLM call.

Usage:
    uv run python scripts/test_integration.py
    uv run python scripts/test_integration.py --model gemini/gemini-2.0-flash
    uv run python scripts/test_integration.py --model anthropic/claude-haiku-4-5-20251001

This runs a trivial local task (no external services needed) to verify:
  1. LLM API call works with your configured model/key
  2. Tool calling works (agent calls bash, gets result)
  3. Metrics collection works (tokens, timing, tool calls)
  4. Results save to results/raw/ as JSON
  5. Verification works against ground truth

Cost: ~1-2K tokens per run (~$0.001 with Haiku/Flash).
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from benchmark.agents.cli_agent import CliAgent
from benchmark.metrics.schemas import RunResult
from benchmark.metrics.verifier import verify_output
from benchmark.tasks.schema import TaskDefinition, VerificationConfig

console = Console()

# A trivial task that only needs local bash — no external services
LOCAL_TEST_TASK = TaskDefinition(
    id="integration_test_01",
    service="local",
    name="List files in current directory",
    complexity="simple_read",
    prompt=(
        'Run the command `ls -1 pyproject.toml README.md METHODOLOGY.md` '
        "and return the output as a JSON array of filenames. "
        "Return ONLY the JSON array, no other text. "
        'Example format: ["file1.txt", "file2.txt"]'
    ),
    prompt_vars={},
    verification=VerificationConfig(
        type="contains",
        ground_truth=["pyproject.toml", "README.md", "METHODOLOGY.md"],
    ),
)


async def run_cli_test(model: str) -> RunResult:
    """Run one CLI agent task with a real LLM call."""
    agent = CliAgent(model=model)
    result = await agent.run(
        task=LOCAL_TEST_TASK,
        run_id="integration-cli-001",
        modality="cli",
        is_cold_start=True,
    )
    return result


def print_result(result: RunResult, verification_passed: bool, score: float) -> None:
    """Pretty-print a run result."""
    table = Table(title=f"Run Result: {result.modality.upper()}", show_header=False)
    table.add_column("Metric", style="bold")
    table.add_column("Value")

    table.add_row("Run ID", result.run_id)
    table.add_row("Model", result.model)
    table.add_row("Task", result.task_id)
    table.add_row("Modality", result.modality)
    table.add_row("Input tokens", str(result.input_tokens))
    table.add_row("Output tokens", str(result.output_tokens))
    table.add_row("Total tokens", str(result.total_tokens))
    table.add_row("Tool calls", str(result.tool_call_count))
    table.add_row("Wall clock (s)", f"{result.wall_clock_seconds:.2f}")
    table.add_row("Completed", "yes" if result.task_completed else "NO")
    table.add_row(
        "Verification",
        f"{'PASS' if verification_passed else 'FAIL'} (score: {score:.1%})",
    )
    if result.error:
        table.add_row("Error", f"[red]{result.error}[/red]")

    console.print(table)

    if result.agent_output:
        console.print(
            Panel(
                result.agent_output[:500],
                title="Agent Output (first 500 chars)",
                border_style="dim",
            )
        )

    if result.tool_calls:
        console.print(f"\n[dim]Tool calls:[/dim]")
        for i, tc in enumerate(result.tool_calls, 1):
            status = "[green]OK[/green]" if tc.success else f"[red]FAIL: {tc.error}[/red]"
            console.print(
                f"  {i}. {tc.tool_name}({json.dumps(tc.tool_input)[:80]}) "
                f"→ {status} [{tc.duration_ms:.0f}ms]"
            )


async def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(description="Integration test for the benchmark framework")
    parser.add_argument(
        "--model",
        default="anthropic/claude-haiku-4-5-20251001",
        help="LiteLLM model string (default: anthropic/claude-haiku-4-5-20251001)",
    )
    parser.add_argument(
        "--output",
        default="results/raw",
        help="Directory to save results (default: results/raw)",
    )
    args = parser.parse_args()

    console.print(Panel(
        f"[bold]Integration Test[/bold]\n"
        f"Model: {args.model}\n"
        f"Task: {LOCAL_TEST_TASK.name}\n"
        f"This will make 1-3 real LLM API calls (~1-2K tokens).",
        title="MCP vs CLI Benchmark",
    ))

    # --- CLI Agent Test ---
    console.print("\n[bold cyan]Running CLI agent...[/bold cyan]")
    try:
        result = await run_cli_test(args.model)
    except Exception as e:
        console.print(f"[red]CLI agent failed: {e}[/red]")
        console.print("\n[yellow]Check your .env file has the right API key set:[/yellow]")
        console.print("  ANTHROPIC_API_KEY for anthropic/* models")
        console.print("  GEMINI_API_KEY for gemini/* models")
        console.print("  OPENAI_API_KEY for openai/* models")
        return

    # Verify
    verification = verify_output(result.agent_output, LOCAL_TEST_TASK.verification)
    print_result(result, verification.passed, verification.score)

    # Save result
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    result_path = output_dir / f"{result.run_id}.json"
    result_path.write_text(result.model_dump_json(indent=2))
    console.print(f"\n[green]Result saved to {result_path}[/green]")

    # Summary
    console.print("\n[bold]Summary:[/bold]")
    if result.task_completed and verification.passed:
        console.print("[green]Integration test PASSED[/green]")
        console.print(f"  LLM call: OK ({result.total_tokens} tokens)")
        console.print(f"  Tool execution: OK ({result.tool_call_count} calls)")
        console.print(f"  Verification: OK ({verification.score:.0%})")
        console.print(f"  Result persistence: OK ({result_path})")
    else:
        console.print("[red]Integration test FAILED[/red]")
        if not result.task_completed:
            console.print(f"  Task did not complete: {result.error}")
        if not verification.passed:
            console.print(f"  Verification failed: {verification.details}")


if __name__ == "__main__":
    asyncio.run(main())
