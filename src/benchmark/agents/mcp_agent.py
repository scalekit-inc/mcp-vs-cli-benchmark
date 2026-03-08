"""Agent that executes tasks via MCP server tools."""

from typing import Any

from mcp import ClientSession

from benchmark.agents.base import BaseAgent


class McpAgent(BaseAgent):
    """Agent that executes tasks via MCP server tools."""

    def __init__(
        self,
        model: str,
        session: ClientSession,
        tools: list[dict[str, Any]],
    ) -> None:
        super().__init__(model=model, tools=tools)
        self.session = session

    @staticmethod
    def mcp_tools_to_anthropic_format(mcp_tools: list) -> list[dict[str, Any]]:
        """Convert MCP tool definitions to Anthropic API tool format."""
        return [
            {
                "name": tool.name,
                "description": tool.description or "",
                "input_schema": tool.inputSchema,
            }
            for tool in mcp_tools
        ]

    async def execute_tool(self, tool_name: str, tool_input: dict) -> str:
        """Execute a tool via the MCP session and return its text output."""
        result = await self.session.call_tool(tool_name, arguments=tool_input)

        parts = []
        for block in result.content:
            if hasattr(block, "text"):
                parts.append(block.text)
            elif hasattr(block, "data"):
                parts.append(str(block.data))
            else:
                parts.append(str(block))

        output = "\n".join(parts)
        if result.isError:
            return f"MCP_ERROR: {output}"
        return output

    @classmethod
    async def from_session(cls, model: str, session: ClientSession) -> "McpAgent":
        """Create an McpAgent by discovering tools from an active MCP session."""
        result = await session.list_tools()
        tools = cls.mcp_tools_to_anthropic_format(result.tools)
        return cls(model=model, session=session, tools=tools)
