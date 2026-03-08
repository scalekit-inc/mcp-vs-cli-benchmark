import json
import time
from pathlib import Path
from typing import Any

import litellm

from benchmark.metrics.collector import MetricsCollector
from benchmark.metrics.schemas import RunResult
from benchmark.tasks.schema import TaskDefinition

SYSTEM_PROMPT_PATH = Path(__file__).parent / "prompts" / "system.md"

# Suppress litellm's verbose logging by default
litellm.suppress_debug_info = True


def _to_openai_tool(tool: dict[str, Any]) -> dict[str, Any]:
    """Convert Anthropic-style tool def to OpenAI-style function calling format.

    Anthropic: {"name", "description", "input_schema"}
    OpenAI:    {"type": "function", "function": {"name", "description", "parameters"}}
    """
    return {
        "type": "function",
        "function": {
            "name": tool["name"],
            "description": tool.get("description", ""),
            "parameters": tool.get("input_schema", tool.get("parameters", {})),
        },
    }


class BaseAgent:
    """Wraps LiteLLM for benchmark runs. Works with any model provider.

    Supports: Anthropic, OpenAI, Google Gemini, Mistral, and 100+ others via LiteLLM.
    Set the model string accordingly (e.g., "anthropic/claude-sonnet-4-20250514",
    "gemini/gemini-2.5-pro", "openai/gpt-4o").
    """

    def __init__(
        self,
        model: str,
        tools: list[dict[str, Any]],
        system_prompt: str | None = None,
    ) -> None:
        self.model = model
        self.tools = tools  # Anthropic format (for backward compat / MCP agent)
        self._openai_tools = [_to_openai_tool(t) for t in tools] if tools else []
        self.system_prompt = system_prompt or self._load_system_prompt()

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
        """Run a single benchmark: send task to LLM, handle tool calls, collect metrics."""
        collector = MetricsCollector(run_id=run_id, task_id=task.id, modality=modality)
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": self.system_prompt},
            *self.build_messages(task),
        ]

        max_turns = 20
        final_text = ""
        error = None

        try:
            for _ in range(max_turns):
                kwargs: dict[str, Any] = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": 0,
                    "max_tokens": 4096,
                }
                if self._openai_tools:
                    kwargs["tools"] = self._openai_tools

                response = litellm.completion(**kwargs)

                usage = response.usage
                collector.record_api_response(
                    input_tokens=usage.prompt_tokens or 0,
                    output_tokens=usage.completion_tokens or 0,
                )

                choice = response.choices[0]
                msg = choice.message

                if msg.content:
                    final_text += msg.content

                tool_calls = msg.tool_calls
                if not tool_calls:
                    break

                # Add assistant message to history
                messages.append(msg.model_dump())

                # Execute each tool call
                for tc in tool_calls:
                    func = tc.function
                    tool_name = func.name
                    tool_input = (
                        json.loads(func.arguments)
                        if isinstance(func.arguments, str)
                        else func.arguments
                    )

                    start = time.monotonic()
                    try:
                        result = await self.execute_tool(tool_name, tool_input)
                        duration_ms = (time.monotonic() - start) * 1000
                        collector.record_tool_call(
                            tool_name=tool_name,
                            tool_input=tool_input,
                            tool_output=result,
                            duration_ms=duration_ms,
                            success=True,
                        )
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": result,
                        })
                    except Exception as e:
                        duration_ms = (time.monotonic() - start) * 1000
                        error_str = str(e)
                        collector.record_tool_call(
                            tool_name=tool_name,
                            tool_input=tool_input,
                            tool_output="",
                            duration_ms=duration_ms,
                            success=False,
                            error=error_str,
                        )
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": f"Error: {error_str}",
                        })

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
