"""Blinded LLM-as-judge with random position assignment.

Evaluates two agent outputs (CLI vs MCP) without revealing which is which,
using random A/B position assignment to eliminate ordering bias.
"""

import json
import random
from typing import Any

import litellm

from benchmark.metrics.schemas import JudgeVerdict

JUDGE_SYSTEM_PROMPT = """\
You are an impartial judge evaluating the quality of two AI agent outputs for the same task.

You do NOT know which system produced which output. Evaluate each independently.

Score each output on a scale of 1-5:
  1 = Completely wrong or empty
  2 = Partially correct but major errors
  3 = Mostly correct but missing important details
  4 = Correct with minor issues
  5 = Perfectly correct and complete

Respond with ONLY a JSON object in this exact format:
{
  "score_a": <int 1-5>,
  "score_b": <int 1-5>,
  "rationale_a": "<brief explanation>",
  "rationale_b": "<brief explanation>"
}
"""


def build_judge_prompt(task_description: str, output_a: str, output_b: str) -> str:
    """Build a blinded judge prompt with two outputs labeled A and B.

    The prompt intentionally avoids any mention of CLI or MCP to prevent bias.
    """
    return f"""\
## Task
{task_description}

## Output A
{output_a}

## Output B
{output_b}

Evaluate both outputs for correctness, completeness, and format compliance.
Score each from 1 (worst) to 5 (best). Respond with JSON only."""


def parse_judge_response(response: str) -> dict[str, Any] | None:
    """Parse the judge's JSON response, returning None if invalid."""
    try:
        data = json.loads(response.strip())
        if all(k in data for k in ("score_a", "score_b", "rationale_a", "rationale_b")):
            return data
        return None
    except json.JSONDecodeError:
        return None


async def judge_outputs(
    task_description: str,
    cli_output: str,
    mcp_output: str,
    cli_run_id: str,
    mcp_run_id: str,
    task_id: str,
    judge_model: str = "claude-opus-4-20250514",
    attempts: int = 3,
) -> tuple[list[JudgeVerdict], list[JudgeVerdict]]:
    """Run blinded LLM-as-judge evaluation with random position assignment.

    Each attempt randomly assigns CLI/MCP outputs to positions A/B to eliminate
    ordering bias. Returns verdict lists for CLI and MCP respectively.

    Args:
        task_description: The task that was evaluated.
        cli_output: Output from the CLI agent.
        mcp_output: Output from the MCP agent.
        cli_run_id: Run ID for the CLI agent.
        mcp_run_id: Run ID for the MCP agent.
        task_id: The task identifier.
        judge_model: Model to use as judge.
        attempts: Number of judging attempts (for consistency).

    Returns:
        Tuple of (cli_verdicts, mcp_verdicts).
    """
    cli_verdicts: list[JudgeVerdict] = []
    mcp_verdicts: list[JudgeVerdict] = []

    for attempt in range(1, attempts + 1):
        cli_is_a = random.random() < 0.5
        if cli_is_a:
            output_a, output_b = cli_output, mcp_output
        else:
            output_a, output_b = mcp_output, cli_output

        prompt = build_judge_prompt(task_description, output_a, output_b)

        response = litellm.completion(
            model=judge_model,
            messages=[
                {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            max_tokens=1024,
            temperature=0,
        )

        text = response.choices[0].message.content or ""
        scores = parse_judge_response(text)

        if scores is None:
            continue

        cli_score = scores["score_a"] if cli_is_a else scores["score_b"]
        mcp_score = scores["score_b"] if cli_is_a else scores["score_a"]
        cli_rationale = scores["rationale_a"] if cli_is_a else scores["rationale_b"]
        mcp_rationale = scores["rationale_b"] if cli_is_a else scores["rationale_a"]

        cli_verdicts.append(JudgeVerdict(
            run_id=cli_run_id, task_id=task_id, quality_score=cli_score,
            rationale=cli_rationale, judge_model=judge_model, attempt=attempt,
        ))
        mcp_verdicts.append(JudgeVerdict(
            run_id=mcp_run_id, task_id=task_id, quality_score=mcp_score,
            rationale=mcp_rationale, judge_model=judge_model, attempt=attempt,
        ))

    return cli_verdicts, mcp_verdicts
