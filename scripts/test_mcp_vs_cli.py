#!/usr/bin/env python3
"""Side-by-side MCP vs CLI integration test using GitHub.

Runs the SAME task via both modalities and compares results:
  - CLI: uses `gh` CLI tool via bash
  - MCP: uses @modelcontextprotocol/server-github via MCP protocol

Usage:
    uv run python scripts/test_mcp_vs_cli.py
    uv run python scripts/test_mcp_vs_cli.py --model gemini/gemini-3.1-flash-lite-preview
    uv run python scripts/test_mcp_vs_cli.py --repo scalekit-inc/mcp-vs-cli-benchmark

Prerequisites:
    - GITHUB_TOKEN in .env (for both CLI and MCP)
    - `gh` CLI installed and authenticated
    - npx available (for GitHub MCP server)
    - Model API key in .env (GEMINI_API_KEY, ANTHROPIC_API_KEY, etc.)

Cost: ~2-4K tokens total (~$0.002 with cheap models).
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from benchmark.agents.cli_agent import CliAgent
from benchmark.agents.mcp_agent import McpAgent
from benchmark.metrics.schemas import RunResult
from benchmark.metrics.verifier import verify_output
from benchmark.tasks.schema import TaskDefinition, VerificationConfig

console = Console()


def make_github_task(repo: str) -> TaskDefinition:
    """Create a simple GitHub read task that works with any public repo."""
    return TaskDefinition(
        id="github_mcp_vs_cli_01",
        service="github",
        name="Get repository language and license",
        complexity="simple_read",
        prompt=(
            f'What is the primary programming language and license of the GitHub repository "{repo}"? '
            "Return a JSON object with two fields: "
            '"language" (string, e.g. "Python") and "license" (string, e.g. "MIT License"). '
            "Return ONLY the JSON object, no other text."
        ),
        prompt_vars={},
        verification=VerificationConfig(
            type="contains",
            # anthropics/anthropic-sdk-python is Python with MIT license
            ground_truth=["Python", "MIT"],
        ),
    )


async def run_cli_agent(model: str, task: TaskDefinition) -> RunResult:
    """Run the task via gh CLI."""
    agent = CliAgent(model=model)
    return await agent.run(
        task=task,
        run_id="comparison-cli-001",
        modality="cli",
        is_cold_start=True,
    )


async def run_mcp_agent(model: str, task: TaskDefinition) -> RunResult:
    """Run the task via GitHub MCP server."""
    github_token = os.environ.get("GITHUB_TOKEN", "")
    if not github_token:
        raise ValueError("GITHUB_TOKEN not set in environment")

    server_params = StdioServerParameters(
        command="npx",
        args=["-y", "@modelcontextprotocol/server-github"],
        env={"GITHUB_PERSONAL_ACCESS_TOKEN": github_token, "PATH": os.environ.get("PATH", "")},
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Discover tools
            tools_result = await session.list_tools()
            tool_names = [t.name for t in tools_result.tools]
            console.print(f"  [dim]MCP server connected — {len(tool_names)} tools available[/dim]")
            console.print(f"  [dim]Tools: {', '.join(tool_names[:10])}{'...' if len(tool_names) > 10 else ''}[/dim]")

            # Create agent with discovered tools
            agent = await McpAgent.from_session(model=model, session=session)

            return await agent.run(
                task=task,
                run_id="comparison-mcp-001",
                modality="mcp",
                is_cold_start=True,
            )


def print_result(result: RunResult) -> None:
    """Print a single run result."""
    table = Table(show_header=False, title=f"{result.modality.upper()} Result")
    table.add_column("Metric", style="bold")
    table.add_column("Value")

    table.add_row("Tokens (in/out)", f"{result.input_tokens} / {result.output_tokens}")
    table.add_row("Total tokens", str(result.total_tokens))
    table.add_row("Tool calls", str(result.tool_call_count))
    table.add_row("Wall clock (s)", f"{result.wall_clock_seconds:.2f}")
    table.add_row("Completed", "yes" if result.task_completed else "NO")
    if result.error:
        table.add_row("Error", f"[red]{result.error}[/red]")

    console.print(table)

    if result.tool_calls:
        for i, tc in enumerate(result.tool_calls, 1):
            status = "[green]OK[/green]" if tc.success else f"[red]FAIL[/red]"
            input_preview = json.dumps(tc.tool_input)[:100]
            console.print(f"  {i}. {tc.tool_name}({input_preview}) → {status} [{tc.duration_ms:.0f}ms]")

    if result.agent_output:
        console.print(Panel(
            result.agent_output[:300],
            title="Output (first 300 chars)",
            border_style="dim",
        ))


def print_comparison(cli_result: RunResult, mcp_result: RunResult) -> None:
    """Print side-by-side comparison."""
    table = Table(title="CLI vs MCP Comparison")
    table.add_column("Metric", style="bold")
    table.add_column("CLI", justify="right")
    table.add_column("MCP", justify="right")
    table.add_column("Winner", justify="center")

    # Tokens
    cli_tok = cli_result.total_tokens
    mcp_tok = mcp_result.total_tokens
    tok_winner = "[green]CLI[/green]" if cli_tok < mcp_tok else "[green]MCP[/green]" if mcp_tok < cli_tok else "Tie"
    table.add_row("Total tokens", str(cli_tok), str(mcp_tok), tok_winner)

    # Tool calls
    cli_tc = cli_result.tool_call_count
    mcp_tc = mcp_result.tool_call_count
    tc_winner = "[green]CLI[/green]" if cli_tc < mcp_tc else "[green]MCP[/green]" if mcp_tc < cli_tc else "Tie"
    table.add_row("Tool calls", str(cli_tc), str(mcp_tc), tc_winner)

    # Wall clock
    cli_wc = cli_result.wall_clock_seconds
    mcp_wc = mcp_result.wall_clock_seconds
    wc_winner = "[green]CLI[/green]" if cli_wc < mcp_wc else "[green]MCP[/green]" if mcp_wc < cli_wc else "Tie"
    table.add_row("Wall clock (s)", f"{cli_wc:.2f}", f"{mcp_wc:.2f}", wc_winner)

    # Completion
    table.add_row(
        "Completed",
        "[green]yes[/green]" if cli_result.task_completed else "[red]no[/red]",
        "[green]yes[/green]" if mcp_result.task_completed else "[red]no[/red]",
        "",
    )

    console.print(table)


async def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(description="MCP vs CLI side-by-side comparison")
    parser.add_argument(
        "--model",
        default=os.environ.get("BENCHMARK_MODEL", "gemini/gemini-3.1-flash-lite-preview"),
        help="LiteLLM model string",
    )
    parser.add_argument(
        "--repo",
        default="anthropics/anthropic-sdk-python",
        help="GitHub repo to query (default: anthropics/anthropic-sdk-python)",
    )
    parser.add_argument(
        "--output",
        default="results/raw",
        help="Directory to save results",
    )
    args = parser.parse_args()

    task = make_github_task(args.repo)

    console.print(Panel(
        f"[bold]MCP vs CLI Comparison[/bold]\n"
        f"Model: {args.model}\n"
        f"Task: Get repo language and license for {args.repo}\n"
        f"This will make ~2-6 real LLM API calls.",
        title="MCP vs CLI Benchmark",
    ))

    # --- CLI Agent ---
    console.print("\n[bold cyan]1. Running CLI agent (gh CLI)...[/bold cyan]")
    try:
        with console.status("[bold cyan]CLI agent thinking..."):
            cli_result = await run_cli_agent(args.model, task)
        cli_verification = verify_output(cli_result.agent_output, task.verification)
        print_result(cli_result)
        console.print(
            f"  Verification: {'[green]PASS[/green]' if cli_verification.passed else '[red]FAIL[/red]'} "
            f"({cli_verification.score:.0%})"
        )
    except Exception as e:
        console.print(f"[red]CLI agent failed: {e}[/red]")
        return

    # --- MCP Agent ---
    console.print("\n[bold cyan]2. Running MCP agent (GitHub MCP server)...[/bold cyan]")
    try:
        console.print("  [dim]Starting GitHub MCP server via npx...[/dim]")
        with console.status("[bold cyan]MCP agent thinking..."):
            mcp_result = await run_mcp_agent(args.model, task)
        mcp_verification = verify_output(mcp_result.agent_output, task.verification)
        print_result(mcp_result)
        console.print(
            f"  Verification: {'[green]PASS[/green]' if mcp_verification.passed else '[red]FAIL[/red]'} "
            f"({mcp_verification.score:.0%})"
        )
    except Exception as e:
        console.print(f"[red]MCP agent failed: {e}[/red]")
        console.print("[yellow]Make sure npx is available and GITHUB_TOKEN is set[/yellow]")
        return

    # --- Comparison ---
    console.print("\n[bold]3. Comparison[/bold]")
    print_comparison(cli_result, mcp_result)

    # Save results
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    for result in [cli_result, mcp_result]:
        path = output_dir / f"{result.run_id}.json"
        path.write_text(result.model_dump_json(indent=2))
    console.print(f"\n[green]Results saved to {output_dir}/[/green]")


if __name__ == "__main__":
    asyncio.run(main())
