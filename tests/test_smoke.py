"""Smoke test: full pipeline with mocked LiteLLM."""
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

    # 2. Mock LiteLLM — first response has tool_calls, second has text only
    mock_tool_call = MagicMock()
    mock_tool_call.id = "call_1"
    mock_tool_call.function.name = "bash"
    mock_tool_call.function.arguments = json.dumps(
        {"command": "echo '[{\"number\": 1, \"title\": \"Test\"}]'"}
    )

    mock_msg_1 = MagicMock()
    mock_msg_1.content = None
    mock_msg_1.tool_calls = [mock_tool_call]
    mock_msg_1.model_dump.return_value = {
        "role": "assistant",
        "content": None,
        "tool_calls": [{"id": "call_1", "type": "function", "function": {"name": "bash", "arguments": "{}"}}],
    }

    mock_msg_2 = MagicMock()
    mock_msg_2.content = '[{"number": 1, "title": "Test"}]'
    mock_msg_2.tool_calls = None

    mock_response_1 = MagicMock()
    mock_response_1.choices = [MagicMock(message=mock_msg_1)]
    mock_response_1.usage = MagicMock(prompt_tokens=100, completion_tokens=50)

    mock_response_2 = MagicMock()
    mock_response_2.choices = [MagicMock(message=mock_msg_2)]
    mock_response_2.usage = MagicMock(prompt_tokens=150, completion_tokens=30)

    with patch("benchmark.agents.base.litellm") as mock_litellm:
        mock_litellm.completion = MagicMock(
            side_effect=[mock_response_1, mock_response_2]
        )
        mock_litellm.suppress_debug_info = True

        agent = CliAgent(model="anthropic/claude-sonnet-4-20250514")
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
