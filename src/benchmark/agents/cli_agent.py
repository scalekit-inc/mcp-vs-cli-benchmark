import asyncio
from typing import Any

from benchmark.agents.base import BaseAgent

BASH_TOOL = {
    "name": "bash",
    "description": (
        "Execute a bash command and return its output (stdout + stderr). "
        "Use this to run CLI tools like gh, psql, gwcli, etc."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "The bash command to execute",
            }
        },
        "required": ["command"],
    },
}


class CliAgent(BaseAgent):
    """Agent that executes tasks via CLI tools (bash commands)."""

    def __init__(self, model: str) -> None:
        super().__init__(model=model, tools=[BASH_TOOL])

    async def execute_tool(self, tool_name: str, tool_input: dict) -> str:
        if tool_name != "bash":
            raise ValueError(f"CLI agent only supports 'bash' tool, got '{tool_name}'")

        command = tool_input["command"]
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)

        output = stdout.decode("utf-8", errors="replace")
        if stderr:
            err = stderr.decode("utf-8", errors="replace")
            if proc.returncode != 0:
                output = f"{output}\nSTDERR: {err}" if output else f"STDERR: {err}"
            else:
                output = f"{output}\n{err}" if output else err

        return output.strip() if output else "(no output)"
