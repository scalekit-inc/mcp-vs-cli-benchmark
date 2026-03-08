"""Tests for BaseAgent — Claude API agentic loop wrapper."""

from unittest.mock import MagicMock, patch

import pytest

from benchmark.tasks.schema import TaskDefinition, VerificationConfig


@pytest.fixture
def sample_task() -> TaskDefinition:
    return TaskDefinition(
        id="test-task-1",
        service="github",
        name="Test Task",
        complexity="simple_read",
        prompt="List all repos for user {username}",
        prompt_vars={"username": "octocat"},
        verification=VerificationConfig(type="contains", ground_truth="octocat"),
    )


@pytest.fixture
def sample_tools() -> list[dict]:
    return [
        {
            "name": "list_repos",
            "description": "List repositories for a user",
            "input_schema": {
                "type": "object",
                "properties": {"username": {"type": "string"}},
                "required": ["username"],
            },
        }
    ]


class TestBaseAgentInit:
    def test_agent_has_tools(self, sample_tools: list[dict]) -> None:
        """Verify that the tools list passed at init is stored on the agent."""
        from benchmark.agents.base import BaseAgent

        agent = BaseAgent(model="claude-sonnet-4-20250514", tools=sample_tools)
        assert agent.tools == sample_tools
        assert len(agent.tools) == 1
        assert agent.tools[0]["name"] == "list_repos"

    def test_agent_loads_system_prompt(self) -> None:
        """Verify that system.md is loaded as the default system prompt."""
        from benchmark.agents.base import BaseAgent

        agent = BaseAgent(model="claude-sonnet-4-20250514", tools=[])
        assert "benchmark agent" in agent.system_prompt.lower()
        assert "tools" in agent.system_prompt.lower()

    def test_agent_custom_system_prompt(self) -> None:
        """Verify that a custom system prompt overrides the default."""
        from benchmark.agents.base import BaseAgent

        custom = "You are a custom agent."
        agent = BaseAgent(model="claude-sonnet-4-20250514", tools=[], system_prompt=custom)
        assert agent.system_prompt == custom


class TestBaseAgentMessages:
    def test_agent_builds_messages_from_task(
        self, sample_task: TaskDefinition, sample_tools: list[dict]
    ) -> None:
        """Verify that rendered prompt appears in the messages list."""
        from benchmark.agents.base import BaseAgent

        agent = BaseAgent(model="claude-sonnet-4-20250514", tools=sample_tools)
        messages = agent.build_messages(sample_task)

        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert "octocat" in messages[0]["content"]
        assert "{username}" not in messages[0]["content"]
