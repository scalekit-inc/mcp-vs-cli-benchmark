import time
from pathlib import Path
from typing import Any

import anthropic

from benchmark.metrics.collector import MetricsCollector
from benchmark.metrics.schemas import RunResult
from benchmark.tasks.schema import TaskDefinition

SYSTEM_PROMPT_PATH = Path(__file__).parent / "prompts" / "system.md"


class BaseAgent:
    """Wraps the Claude API for benchmark runs. Subclass for CLI/MCP specifics."""

    def __init__(
        self,
        model: str,
        tools: list[dict[str, Any]],
        system_prompt: str | None = None,
    ) -> None:
        self.model = model
        self.tools = tools
        self.system_prompt = system_prompt or self._load_system_prompt()
        self.client = anthropic.Anthropic()

    def _load_system_prompt(self) -> str:
        if SYSTEM_PROMPT_PATH.exists():
            return SYSTEM_PROMPT_PATH.read_text()
        return "You are a benchmark agent. Complete the task using the tools provided."

    def build_messages(self, task: TaskDefinition) -> list[dict[str, Any]]:
        return [{"role": "user", "content": task.rendered_prompt()}]

    async def execute_tool(self, tool_name: str, tool_input: dict) -> str:
        """Execute a tool call. Override in subclasses for CLI vs MCP."""
        raise NotImplementedError

    async def run(
        self,
        task: TaskDefinition,
        run_id: str,
        modality: str,
        is_cold_start: bool = False,
    ) -> RunResult:
        """Run a single benchmark: send task to Claude, handle tool calls, collect metrics."""
        collector = MetricsCollector(run_id=run_id, task_id=task.id, modality=modality)
        messages = self.build_messages(task)

        max_turns = 20
        final_text = ""
        error = None

        try:
            for _ in range(max_turns):
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=4096,
                    temperature=0,
                    system=self.system_prompt,
                    tools=self.tools,
                    messages=messages,
                )

                collector.record_api_response(
                    input_tokens=response.usage.input_tokens,
                    output_tokens=response.usage.output_tokens,
                )

                tool_use_blocks = []
                for block in response.content:
                    if block.type == "text":
                        final_text += block.text
                    elif block.type == "tool_use":
                        tool_use_blocks.append(block)

                if not tool_use_blocks:
                    break

                messages.append({"role": "assistant", "content": response.content})

                tool_results = []
                for tool_block in tool_use_blocks:
                    start = time.monotonic()
                    try:
                        result = await self.execute_tool(
                            tool_block.name, tool_block.input
                        )
                        duration_ms = (time.monotonic() - start) * 1000
                        collector.record_tool_call(
                            tool_name=tool_block.name,
                            tool_input=tool_block.input,
                            tool_output=result,
                            duration_ms=duration_ms,
                            success=True,
                        )
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_block.id,
                            "content": result,
                        })
                    except Exception as e:
                        duration_ms = (time.monotonic() - start) * 1000
                        error_str = str(e)
                        collector.record_tool_call(
                            tool_name=tool_block.name,
                            tool_input=tool_block.input,
                            tool_output="",
                            duration_ms=duration_ms,
                            success=False,
                            error=error_str,
                        )
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_block.id,
                            "content": f"Error: {error_str}",
                            "is_error": True,
                        })

                messages.append({"role": "user", "content": tool_results})

        except Exception as e:
            error = str(e)

        return collector.finalize(
            model=self.model,
            agent_output=final_text,
            task_completed=error is None and len(final_text) > 0,
            completion_score=1.0 if error is None else 0.0,
            is_cold_start=is_cold_start,
            error=error,
        )
