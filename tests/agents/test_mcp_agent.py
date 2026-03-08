"""Tests for McpAgent — MCP client SDK based tool execution."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from benchmark.agents.mcp_agent import McpAgent


@pytest.fixture
def mock_mcp_tools():
    """Simulate MCP tool objects returned by session.list_tools()."""
    return [
        SimpleNamespace(
            name="read_file",
            description="Read a file from disk",
            inputSchema={
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        ),
        SimpleNamespace(
            name="write_file",
            description="Write content to a file",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
            },
        ),
    ]


@pytest.fixture
def converted_tools():
    """Pre-converted Anthropic-format tools."""
    return [
        {
            "name": "read_file",
            "description": "Read a file from disk",
            "input_schema": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        },
    ]


@pytest.fixture
def mock_session():
    session = AsyncMock()
    return session


class TestMcpToolsToAnthropicFormat:
    def test_mcp_agent_builds_tools_from_server_capabilities(self, mock_mcp_tools):
        result = McpAgent.mcp_tools_to_anthropic_format(mock_mcp_tools)

        assert len(result) == 2

        assert result[0]["name"] == "read_file"
        assert result[0]["description"] == "Read a file from disk"
        assert result[0]["input_schema"]["type"] == "object"
        assert "path" in result[0]["input_schema"]["properties"]

        assert result[1]["name"] == "write_file"
        assert result[1]["description"] == "Write content to a file"
        assert "path" in result[1]["input_schema"]["properties"]
        assert "content" in result[1]["input_schema"]["properties"]


class TestMcpAgentInit:
    def test_mcp_agent_has_tools(self, mock_session, converted_tools):
        agent = McpAgent(model="claude-sonnet-4-20250514", session=mock_session, tools=converted_tools)

        assert agent.tools == converted_tools
        assert agent.session is mock_session
        assert agent.model == "claude-sonnet-4-20250514"


class TestMcpAgentExecuteTool:
    @pytest.mark.asyncio
    async def test_mcp_agent_execute_tool_returns_text(self, mock_session, converted_tools):
        # Mock call_tool to return a result with text content blocks
        text_block = SimpleNamespace(text="file contents here")
        call_result = SimpleNamespace(
            content=[text_block],
            isError=False,
        )
        mock_session.call_tool = AsyncMock(return_value=call_result)

        agent = McpAgent(model="claude-sonnet-4-20250514", session=mock_session, tools=converted_tools)
        output = await agent.execute_tool("read_file", {"path": "/tmp/test.txt"})

        assert output == "file contents here"
        mock_session.call_tool.assert_awaited_once_with("read_file", arguments={"path": "/tmp/test.txt"})

    @pytest.mark.asyncio
    async def test_mcp_agent_execute_tool_error_prefixed(self, mock_session, converted_tools):
        text_block = SimpleNamespace(text="something went wrong")
        call_result = SimpleNamespace(
            content=[text_block],
            isError=True,
        )
        mock_session.call_tool = AsyncMock(return_value=call_result)

        agent = McpAgent(model="claude-sonnet-4-20250514", session=mock_session, tools=converted_tools)
        output = await agent.execute_tool("bad_tool", {"x": 1})

        assert output.startswith("MCP_ERROR:")
        assert "something went wrong" in output
