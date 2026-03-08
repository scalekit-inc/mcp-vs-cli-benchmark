from typing import Any, Literal
from pydantic import BaseModel


class VerificationConfig(BaseModel):
    """How to verify a task's output."""
    type: Literal["exact_match", "contains", "llm_judge", "api_check"]
    ground_truth: Any = None
    check_endpoint: str | None = None
    judge_prompt: str | None = None


class TaskDefinition(BaseModel):
    """A single benchmark task loaded from YAML."""
    id: str
    service: str
    name: str
    complexity: Literal[
        "simple_read", "multi_step_read", "simple_write",
        "complex_read", "multi_step_write"
    ]
    prompt: str
    prompt_vars: dict[str, str] = {}
    verification: VerificationConfig

    def rendered_prompt(self) -> str:
        """Return prompt with variables substituted."""
        result = self.prompt
        for key, value in self.prompt_vars.items():
            result = result.replace(f"{{{key}}}", value)
        return result
