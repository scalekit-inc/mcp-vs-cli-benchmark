"""Smoke test: full pipeline with mocked Claude API."""
import json
from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_full_pipeline_smoke():
    from benchmark.agents.cli_agent import CliAgent
    from benchmark.metrics.schemas import RunResult
    from benchmark.metrics.verifier import verify_output
    from benchmark.tasks.schema import TaskDefinition, VerificationConfig

    # 1. Simple task
    task = TaskDefinition(
        id="smoke_01",
        service="test",
        name="Echo test",
        complexity="simple_read",
        prompt='Run: echo \'[{"number": 1, "title": "Test"}]\' and return its output.',
        prompt_vars={},
        verification=VerificationConfig(
            type="exact_match",
            ground_truth=[{"number": 1, "title": "Test"}],
        ),
    )

    # 2. Mock Claude API — first response has tool_use, second has text
    mock_tool_block = MagicMock()
    mock_tool_block.type = "tool_use"
    mock_tool_block.name = "bash"
    mock_tool_block.input = {"command": "echo '[{\"number\": 1, \"title\": \"Test\"}]'"}
    mock_tool_block.id = "tool_1"

    mock_text_block = MagicMock()
    mock_text_block.type = "text"
    mock_text_block.text = '[{"number": 1, "title": "Test"}]'

    mock_response_1 = MagicMock()
    mock_response_1.content = [mock_tool_block]
    mock_response_1.usage = MagicMock(input_tokens=100, output_tokens=50)

    mock_response_2 = MagicMock()
    mock_response_2.content = [mock_text_block]
    mock_response_2.usage = MagicMock(input_tokens=150, output_tokens=30)

    with patch("benchmark.agents.base.anthropic") as mock_anthropic:
        mock_client = MagicMock()
        mock_client.messages.create = MagicMock(
            side_effect=[mock_response_1, mock_response_2]
        )
        mock_anthropic.Anthropic.return_value = mock_client

        agent = CliAgent(model="claude-sonnet-4-20250514")
        result = await agent.run(
            task=task,
            run_id="smoke-test-001",
            modality="cli",
            is_cold_start=False,
        )

    # 3. Verify metrics
    assert isinstance(result, RunResult)
    assert result.run_id == "smoke-test-001"
    assert result.total_tokens == 330
    assert result.tool_call_count == 1
    assert result.task_completed is True

    # 4. Verify output against ground truth
    verification = verify_output(result.agent_output, task.verification)
    assert verification.passed is True
    assert verification.score == 1.0

    # 5. Verify JSON roundtrip
    json_str = result.model_dump_json()
    restored = RunResult.model_validate_json(json_str)
    assert restored.run_id == "smoke-test-001"
