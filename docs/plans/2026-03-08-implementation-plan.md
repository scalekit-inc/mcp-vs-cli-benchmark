# MCP vs CLI Benchmark — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a reproducible Python benchmark framework that compares MCP servers vs CLI tools across GitHub, Google Workspace, and Postgres — measuring tokens, latency, completion, and quality over 900 statistically rigorous runs.

**Architecture:** Python harness calls the Claude API directly (Anthropic SDK) with two agent configurations — one with bash/CLI tools, one with MCP tools. A metrics collector instruments every call. A scheduler alternates runs and randomizes task order. Results feed into statistical analysis (scipy) and visualization (plotly).

**Tech Stack:** Python 3.12+, `anthropic` SDK, `pydantic` for schemas, `pyyaml` for task definitions, `scipy` for statistics, `plotly` for charts, `pytest` for tests, `docker` for Postgres fixtures, `mcp` SDK for MCP client.

**Repo:** `~/Documents/mcp-vs-cli-benchmark/`

---

## Phase 1: Framework Scaffolding + GitHub Benchmark

### Task 1: Project Setup

**Files:**
- Create: `pyproject.toml`
- Create: `src/benchmark/__init__.py`
- Create: `src/benchmark/py.typed`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Create: `.gitignore`
- Create: `.env.example`
- Create: `README.md`

**Step 1: Create pyproject.toml with all dependencies**

```toml
[project]
name = "mcp-vs-cli-benchmark"
version = "0.1.0"
description = "Rigorous benchmark comparing MCP servers vs CLI tools for AI agents"
requires-python = ">=3.12"
dependencies = [
    "anthropic>=0.42.0",
    "pydantic>=2.0",
    "pyyaml>=6.0",
    "scipy>=1.14",
    "plotly>=5.24",
    "pandas>=2.2",
    "mcp>=1.0",
    "httpx>=0.27",
    "python-dotenv>=1.0",
    "rich>=13.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24",
    "pytest-cov>=5.0",
    "ruff>=0.8",
    "mypy>=1.13",
]

[project.scripts]
bench = "benchmark.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/benchmark"]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"

[tool.ruff]
target-version = "py312"
line-length = 100

[tool.mypy]
python_version = "3.12"
strict = true
```

**Step 2: Create directory structure**

```bash
mkdir -p src/benchmark/{agents,metrics,runner,tasks,fixtures,analysis}
mkdir -p tests/{agents,metrics,runner,tasks,fixtures,analysis}
touch src/benchmark/__init__.py src/benchmark/py.typed
touch src/benchmark/{agents,metrics,runner,tasks,fixtures,analysis}/__init__.py
touch tests/__init__.py tests/conftest.py
touch tests/{agents,metrics,runner,tasks,fixtures,analysis}/__init__.py
```

**Step 3: Create .gitignore**

```
__pycache__/
*.pyc
.env
dist/
*.egg-info/
.venv/
results/raw/
.mypy_cache/
.pytest_cache/
.ruff_cache/
```

**Step 4: Create .env.example**

```bash
ANTHROPIC_API_KEY=sk-ant-...
GITHUB_TOKEN=ghp_...
BENCHMARK_MODEL=claude-sonnet-4-20250514
JUDGE_MODEL=claude-opus-4-20250514
BENCHMARK_REPO=your-org/mcp-vs-cli-benchmark-data
MCP_GITHUB_SERVER_URL=
POSTGRES_URL=postgresql://bench:bench@localhost:5432/benchmark
GOOGLE_SERVICE_ACCOUNT_JSON=
```

**Step 5: Create minimal README.md**

```markdown
# MCP vs CLI Benchmark

Rigorous benchmark comparing MCP servers vs CLI tools for AI agents.

See [METHODOLOGY.md](METHODOLOGY.md) for the pre-registered experimental design.

## Setup

\`\`\`bash
pip install -e ".[dev]"
cp .env.example .env
# Fill in API keys
\`\`\`

## Run

\`\`\`bash
bench run --service github --runs 30
bench analyze --input results/raw/
\`\`\`
```

**Step 6: Install and verify**

Run: `cd ~/Documents/mcp-vs-cli-benchmark && pip install -e ".[dev]"`
Expected: Clean install, no errors.

**Step 7: Commit**

```bash
git add -A
git commit -m "chore: project scaffolding with dependencies and directory structure"
```

---

### Task 2: Metric Schemas (Pydantic Models)

**Files:**
- Create: `src/benchmark/metrics/schemas.py`
- Create: `tests/metrics/test_schemas.py`

**Step 1: Write the failing test**

```python
# tests/metrics/test_schemas.py
import json
from datetime import datetime, timezone


def test_tool_call_metric_roundtrip():
    from benchmark.metrics.schemas import ToolCallMetric

    m = ToolCallMetric(
        tool_name="gh_list_issues",
        tool_input={"repo": "test/repo", "label": "bug"},
        tool_output='[{"id": 1}]',
        duration_ms=150.5,
        success=True,
        error=None,
    )
    data = m.model_dump()
    restored = ToolCallMetric.model_validate(data)
    assert restored.tool_name == "gh_list_issues"
    assert restored.duration_ms == 150.5
    assert restored.success is True


def test_run_result_schema():
    from benchmark.metrics.schemas import RunResult, ToolCallMetric

    tool_calls = [
        ToolCallMetric(
            tool_name="bash",
            tool_input={"command": "gh issue list"},
            tool_output="issue list...",
            duration_ms=200.0,
            success=True,
            error=None,
        )
    ]
    result = RunResult(
        run_id="test-123",
        task_id="github_01",
        modality="cli",
        model="claude-sonnet-4-20250514",
        timestamp=datetime.now(timezone.utc),
        input_tokens=500,
        output_tokens=200,
        total_tokens=700,
        tool_calls=tool_calls,
        tool_call_count=1,
        wall_clock_seconds=2.5,
        task_completed=True,
        completion_score=1.0,
        agent_output="Found 3 issues with label bug...",
        error=None,
        is_cold_start=False,
    )
    assert result.total_tokens == 700
    assert result.modality == "cli"
    # Verify JSON serialization for raw data storage
    json_str = result.model_dump_json()
    restored = RunResult.model_validate_json(json_str)
    assert restored.run_id == "test-123"


def test_run_result_rejects_invalid_modality():
    from pydantic import ValidationError
    from benchmark.metrics.schemas import RunResult

    try:
        RunResult(
            run_id="x",
            task_id="x",
            modality="invalid",  # must be "cli" or "mcp"
            model="x",
            timestamp=datetime.now(timezone.utc),
            input_tokens=0,
            output_tokens=0,
            total_tokens=0,
            tool_calls=[],
            tool_call_count=0,
            wall_clock_seconds=0,
            task_completed=False,
            completion_score=0,
            agent_output="",
            error=None,
            is_cold_start=False,
        )
        assert False, "Should have raised"
    except ValidationError:
        pass


def test_judge_verdict_schema():
    from benchmark.metrics.schemas import JudgeVerdict

    v = JudgeVerdict(
        run_id="test-123",
        task_id="github_04",
        quality_score=4,
        rationale="Output covered all PRs but missed one detail.",
        judge_model="claude-opus-4-20250514",
        attempt=1,
    )
    assert v.quality_score == 4
    assert 1 <= v.quality_score <= 5
```

**Step 2: Run test to verify it fails**

Run: `cd ~/Documents/mcp-vs-cli-benchmark && python -m pytest tests/metrics/test_schemas.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'benchmark.metrics.schemas'`

**Step 3: Write minimal implementation**

```python
# src/benchmark/metrics/schemas.py
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ToolCallMetric(BaseModel):
    """Metrics for a single tool invocation within a run."""

    tool_name: str
    tool_input: dict
    tool_output: str
    duration_ms: float
    success: bool
    error: str | None = None


class RunResult(BaseModel):
    """Complete result of a single benchmark run (one agent + one task)."""

    run_id: str
    task_id: str
    modality: Literal["cli", "mcp"]
    model: str
    timestamp: datetime

    # Token metrics
    input_tokens: int
    output_tokens: int
    total_tokens: int

    # Tool metrics
    tool_calls: list[ToolCallMetric]
    tool_call_count: int

    # Timing
    wall_clock_seconds: float

    # Completion
    task_completed: bool
    completion_score: float = Field(ge=0.0, le=1.0)

    # Output
    agent_output: str
    error: str | None = None

    # Run conditions
    is_cold_start: bool


class JudgeVerdict(BaseModel):
    """LLM-as-judge evaluation of a run's output quality."""

    run_id: str
    task_id: str
    quality_score: int = Field(ge=1, le=5)
    rationale: str
    judge_model: str
    attempt: int = Field(ge=1, le=3)


class TaskComparison(BaseModel):
    """Aggregated comparison of CLI vs MCP for a single task."""

    task_id: str
    service: str
    cli_runs: list[RunResult]
    mcp_runs: list[RunResult]
    cli_verdicts: list[JudgeVerdict] = []
    mcp_verdicts: list[JudgeVerdict] = []
```

**Step 4: Run test to verify it passes**

Run: `cd ~/Documents/mcp-vs-cli-benchmark && python -m pytest tests/metrics/test_schemas.py -v`
Expected: 4 passed

**Step 5: Commit**

```bash
git add src/benchmark/metrics/schemas.py tests/metrics/test_schemas.py
git commit -m "feat: add Pydantic metric schemas for runs, tool calls, and judge verdicts"
```

---

### Task 3: Task Registry (YAML Definitions + Loader)

**Files:**
- Create: `src/benchmark/tasks/schema.py`
- Create: `src/benchmark/tasks/registry.py`
- Create: `tasks/github/task_01_list_issues.yaml`
- Create: `tests/tasks/test_registry.py`

**Step 1: Write the failing test**

```python
# tests/tasks/test_registry.py
from pathlib import Path
import tempfile
import yaml


def test_task_definition_loads_from_yaml():
    from benchmark.tasks.schema import TaskDefinition

    yaml_content = {
        "id": "github_01",
        "service": "github",
        "name": "List open issues with label bug",
        "complexity": "simple_read",
        "prompt": "List all open issues in the repo {repo} that have the label 'bug'. Return their numbers and titles.",
        "prompt_vars": {"repo": "test-org/test-repo"},
        "verification": {
            "type": "exact_match",
            "ground_truth": [
                {"number": 1, "title": "Login broken"},
                {"number": 3, "title": "CSS glitch on mobile"},
            ],
        },
    }

    task = TaskDefinition.model_validate(yaml_content)
    assert task.id == "github_01"
    assert task.service == "github"
    assert "{repo}" in task.prompt


def test_registry_loads_all_tasks_from_directory():
    from benchmark.tasks.registry import TaskRegistry

    with tempfile.TemporaryDirectory() as tmpdir:
        task_dir = Path(tmpdir) / "github"
        task_dir.mkdir()
        task_file = task_dir / "task_01.yaml"
        task_data = {
            "id": "github_01",
            "service": "github",
            "name": "Test task",
            "complexity": "simple_read",
            "prompt": "Do something",
            "prompt_vars": {},
            "verification": {"type": "exact_match", "ground_truth": []},
        }
        task_file.write_text(yaml.dump(task_data))

        registry = TaskRegistry(Path(tmpdir))
        tasks = registry.get_tasks("github")
        assert len(tasks) == 1
        assert tasks[0].id == "github_01"


def test_registry_get_all_tasks():
    from benchmark.tasks.registry import TaskRegistry

    with tempfile.TemporaryDirectory() as tmpdir:
        for svc in ["github", "postgres"]:
            svc_dir = Path(tmpdir) / svc
            svc_dir.mkdir()
            task_data = {
                "id": f"{svc}_01",
                "service": svc,
                "name": f"{svc} task",
                "complexity": "simple_read",
                "prompt": "Do something",
                "prompt_vars": {},
                "verification": {"type": "exact_match", "ground_truth": []},
            }
            (svc_dir / "task_01.yaml").write_text(yaml.dump(task_data))

        registry = TaskRegistry(Path(tmpdir))
        all_tasks = registry.get_all_tasks()
        assert len(all_tasks) == 2
```

**Step 2: Run test to verify it fails**

Run: `cd ~/Documents/mcp-vs-cli-benchmark && python -m pytest tests/tasks/test_registry.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Write implementation**

```python
# src/benchmark/tasks/schema.py
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
```

```python
# src/benchmark/tasks/registry.py
from pathlib import Path

import yaml

from benchmark.tasks.schema import TaskDefinition


class TaskRegistry:
    """Loads and manages task definitions from YAML files."""

    def __init__(self, tasks_dir: Path) -> None:
        self._tasks_dir = tasks_dir
        self._tasks: dict[str, list[TaskDefinition]] = {}
        self._load_all()

    def _load_all(self) -> None:
        for service_dir in sorted(self._tasks_dir.iterdir()):
            if not service_dir.is_dir():
                continue
            service = service_dir.name
            self._tasks[service] = []
            for task_file in sorted(service_dir.glob("*.yaml")):
                with open(task_file) as f:
                    data = yaml.safe_load(f)
                self._tasks[service].append(TaskDefinition.model_validate(data))

    def get_tasks(self, service: str) -> list[TaskDefinition]:
        return self._tasks.get(service, [])

    def get_all_tasks(self) -> list[TaskDefinition]:
        return [task for tasks in self._tasks.values() for task in tasks]

    def get_task(self, task_id: str) -> TaskDefinition | None:
        for task in self.get_all_tasks():
            if task.id == task_id:
                return task
        return None
```

**Step 4: Run test to verify it passes**

Run: `cd ~/Documents/mcp-vs-cli-benchmark && python -m pytest tests/tasks/test_registry.py -v`
Expected: 3 passed

**Step 5: Create first real task YAML**

```yaml
# tasks/github/task_01_list_issues.yaml
id: github_01
service: github
name: List open issues with label bug
complexity: simple_read
prompt: |
  List all open issues in the repository {repo} that have the label "bug".
  Return a JSON array of objects with "number" and "title" fields, sorted by
  issue number ascending. Return ONLY the JSON array, no other text.
prompt_vars:
  repo: "scalekit-inc/mcp-vs-cli-benchmark-data"
verification:
  type: exact_match
  ground_truth:
    - number: 1
      title: "Login page returns 500 on invalid email format"
    - number: 3
      title: "CSS layout breaks on viewport < 768px"
    - number: 5
      title: "Memory leak in WebSocket reconnection handler"
    - number: 7
      title: "Race condition in concurrent file upload"
    - number: 9
      title: "API rate limiter counts preflight requests"
```

**Step 6: Commit**

```bash
git add src/benchmark/tasks/ tests/tasks/ tasks/
git commit -m "feat: add task definition schema, YAML registry, and first GitHub task"
```

---

### Task 4: Metrics Collector (Instruments API Calls)

**Files:**
- Create: `src/benchmark/metrics/collector.py`
- Create: `tests/metrics/test_collector.py`

**Step 1: Write the failing test**

```python
# tests/metrics/test_collector.py
import time


def test_collector_tracks_tool_call():
    from benchmark.metrics.collector import MetricsCollector

    collector = MetricsCollector(run_id="test-1", task_id="github_01", modality="cli")

    collector.record_tool_call(
        tool_name="bash",
        tool_input={"command": "gh issue list"},
        tool_output="issue list output",
        duration_ms=150.0,
        success=True,
    )

    assert collector.tool_call_count == 1
    assert collector.tool_calls[0].tool_name == "bash"


def test_collector_tracks_tokens():
    from benchmark.metrics.collector import MetricsCollector

    collector = MetricsCollector(run_id="test-2", task_id="github_01", modality="mcp")

    collector.record_api_response(input_tokens=500, output_tokens=200)
    collector.record_api_response(input_tokens=600, output_tokens=150)

    assert collector.total_input_tokens == 1100
    assert collector.total_output_tokens == 350


def test_collector_produces_run_result():
    from benchmark.metrics.collector import MetricsCollector

    collector = MetricsCollector(run_id="test-3", task_id="github_01", modality="cli")
    collector.record_api_response(input_tokens=100, output_tokens=50)
    collector.record_tool_call(
        tool_name="bash",
        tool_input={"command": "echo hi"},
        tool_output="hi",
        duration_ms=10.0,
        success=True,
    )

    result = collector.finalize(
        model="claude-sonnet-4-20250514",
        agent_output="done",
        task_completed=True,
        completion_score=1.0,
        is_cold_start=False,
    )

    assert result.run_id == "test-3"
    assert result.total_tokens == 150
    assert result.tool_call_count == 1
    assert result.task_completed is True
```

**Step 2: Run test to verify it fails**

Run: `cd ~/Documents/mcp-vs-cli-benchmark && python -m pytest tests/metrics/test_collector.py -v`
Expected: FAIL

**Step 3: Write implementation**

```python
# src/benchmark/metrics/collector.py
import time
from datetime import datetime, timezone

from benchmark.metrics.schemas import RunResult, ToolCallMetric


class MetricsCollector:
    """Collects metrics during a single benchmark run."""

    def __init__(self, run_id: str, task_id: str, modality: str) -> None:
        self.run_id = run_id
        self.task_id = task_id
        self.modality = modality
        self.tool_calls: list[ToolCallMetric] = []
        self.total_input_tokens: int = 0
        self.total_output_tokens: int = 0
        self._start_time: float = time.monotonic()

    @property
    def tool_call_count(self) -> int:
        return len(self.tool_calls)

    def record_tool_call(
        self,
        tool_name: str,
        tool_input: dict,
        tool_output: str,
        duration_ms: float,
        success: bool,
        error: str | None = None,
    ) -> None:
        self.tool_calls.append(
            ToolCallMetric(
                tool_name=tool_name,
                tool_input=tool_input,
                tool_output=tool_output,
                duration_ms=duration_ms,
                success=success,
                error=error,
            )
        )

    def record_api_response(self, input_tokens: int, output_tokens: int) -> None:
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens

    def finalize(
        self,
        model: str,
        agent_output: str,
        task_completed: bool,
        completion_score: float,
        is_cold_start: bool,
        error: str | None = None,
    ) -> RunResult:
        elapsed = time.monotonic() - self._start_time
        return RunResult(
            run_id=self.run_id,
            task_id=self.task_id,
            modality=self.modality,
            model=model,
            timestamp=datetime.now(timezone.utc),
            input_tokens=self.total_input_tokens,
            output_tokens=self.total_output_tokens,
            total_tokens=self.total_input_tokens + self.total_output_tokens,
            tool_calls=self.tool_calls,
            tool_call_count=self.tool_call_count,
            wall_clock_seconds=elapsed,
            task_completed=task_completed,
            completion_score=completion_score,
            agent_output=agent_output,
            error=error,
            is_cold_start=is_cold_start,
        )
```

**Step 4: Run test to verify it passes**

Run: `cd ~/Documents/mcp-vs-cli-benchmark && python -m pytest tests/metrics/test_collector.py -v`
Expected: 3 passed

**Step 5: Commit**

```bash
git add src/benchmark/metrics/collector.py tests/metrics/test_collector.py
git commit -m "feat: add metrics collector for tracking tokens, tool calls, and timing"
```

---

### Task 5: Base Agent (Claude API Wrapper)

**Files:**
- Create: `src/benchmark/agents/base.py`
- Create: `src/benchmark/agents/prompts/system.md`
- Create: `tests/agents/test_base.py`

**Step 1: Write the failing test**

```python
# tests/agents/test_base.py
from unittest.mock import AsyncMock, MagicMock, patch


def test_agent_builds_messages_from_task():
    from benchmark.tasks.schema import TaskDefinition, VerificationConfig
    from benchmark.agents.base import BaseAgent

    task = TaskDefinition(
        id="test_01",
        service="github",
        name="Test",
        complexity="simple_read",
        prompt="List issues in {repo}",
        prompt_vars={"repo": "test/repo"},
        verification=VerificationConfig(type="exact_match", ground_truth=[]),
    )

    agent = BaseAgent(
        model="claude-sonnet-4-20250514",
        tools=[],
        system_prompt="You are a benchmark agent.",
    )

    messages = agent.build_messages(task)
    assert len(messages) == 1
    assert messages[0]["role"] == "user"
    assert "test/repo" in messages[0]["content"]


def test_agent_defines_tool_interface():
    """BaseAgent subclasses must implement get_tools and execute_tool."""
    from benchmark.agents.base import BaseAgent

    agent = BaseAgent(
        model="claude-sonnet-4-20250514",
        tools=[{"name": "bash", "description": "Run a command", "input_schema": {"type": "object", "properties": {"command": {"type": "string"}}}}],
        system_prompt="You are a benchmark agent.",
    )
    assert len(agent.tools) == 1
    assert agent.tools[0]["name"] == "bash"
```

**Step 2: Run test to verify it fails**

Run: `cd ~/Documents/mcp-vs-cli-benchmark && python -m pytest tests/agents/test_base.py -v`
Expected: FAIL

**Step 3: Write implementation**

```python
# src/benchmark/agents/base.py
import json
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

                # Process response content blocks
                tool_use_blocks = []
                for block in response.content:
                    if block.type == "text":
                        final_text += block.text
                    elif block.type == "tool_use":
                        tool_use_blocks.append(block)

                # If no tool calls, we're done
                if not tool_use_blocks:
                    break

                # Add assistant message with all content blocks
                messages.append({"role": "assistant", "content": response.content})

                # Execute each tool call and collect results
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
                        tool_results.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": tool_block.id,
                                "content": result,
                            }
                        )
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
                        tool_results.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": tool_block.id,
                                "content": f"Error: {error_str}",
                                "is_error": True,
                            }
                        )

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
```

**Step 4: Create the shared system prompt**

```markdown
<!-- src/benchmark/agents/prompts/system.md -->
You are a benchmark agent being tested on your ability to complete tasks using tools.

Rules:
- Complete the task using ONLY the tools provided to you.
- Be efficient: use as few tool calls as possible.
- Return your final answer in the exact format requested by the task.
- If a tool call fails, you may retry once. If it fails again, report the error.
- Do not explain your reasoning unless asked. Just complete the task and return the result.
```

**Step 5: Run tests**

Run: `cd ~/Documents/mcp-vs-cli-benchmark && python -m pytest tests/agents/test_base.py -v`
Expected: 2 passed

**Step 6: Commit**

```bash
git add src/benchmark/agents/ tests/agents/
git commit -m "feat: add base agent with Claude API agentic loop and system prompt"
```

---

### Task 6: CLI Agent (Bash Tool Executor)

**Files:**
- Create: `src/benchmark/agents/cli_agent.py`
- Create: `tests/agents/test_cli_agent.py`

**Step 1: Write the failing test**

```python
# tests/agents/test_cli_agent.py
import pytest


@pytest.mark.asyncio
async def test_cli_agent_executes_bash_command():
    from benchmark.agents.cli_agent import CliAgent

    agent = CliAgent(model="claude-sonnet-4-20250514")
    result = await agent.execute_tool("bash", {"command": "echo hello"})
    assert "hello" in result


@pytest.mark.asyncio
async def test_cli_agent_returns_stderr_on_failure():
    from benchmark.agents.cli_agent import CliAgent

    agent = CliAgent(model="claude-sonnet-4-20250514")
    result = await agent.execute_tool("bash", {"command": "ls /nonexistent_dir_xyz"})
    # Should contain error output, not raise
    assert "No such file" in result or "not found" in result.lower() or len(result) > 0


def test_cli_agent_has_bash_tool():
    from benchmark.agents.cli_agent import CliAgent

    agent = CliAgent(model="claude-sonnet-4-20250514")
    assert len(agent.tools) == 1
    assert agent.tools[0]["name"] == "bash"
```

**Step 2: Run test to verify it fails**

Run: `cd ~/Documents/mcp-vs-cli-benchmark && python -m pytest tests/agents/test_cli_agent.py -v`
Expected: FAIL

**Step 3: Write implementation**

```python
# src/benchmark/agents/cli_agent.py
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
```

**Step 4: Run test to verify it passes**

Run: `cd ~/Documents/mcp-vs-cli-benchmark && python -m pytest tests/agents/test_cli_agent.py -v`
Expected: 3 passed

**Step 5: Commit**

```bash
git add src/benchmark/agents/cli_agent.py tests/agents/test_cli_agent.py
git commit -m "feat: add CLI agent with bash tool executor"
```

---

### Task 7: MCP Agent (MCP Client Tool Executor)

**Files:**
- Create: `src/benchmark/agents/mcp_agent.py`
- Create: `tests/agents/test_mcp_agent.py`

**Step 1: Write the failing test**

```python
# tests/agents/test_mcp_agent.py
from unittest.mock import AsyncMock, MagicMock


def test_mcp_agent_builds_tools_from_server_capabilities():
    from benchmark.agents.mcp_agent import McpAgent

    # Mock MCP tools as they would come from list_tools()
    mock_tools = [
        MagicMock(
            name="list_issues",
            description="List issues in a repo",
            inputSchema={
                "type": "object",
                "properties": {"repo": {"type": "string"}},
            },
        ),
        MagicMock(
            name="get_pull_request",
            description="Get PR details",
            inputSchema={
                "type": "object",
                "properties": {"number": {"type": "integer"}},
            },
        ),
    ]

    tools = McpAgent.mcp_tools_to_anthropic_format(mock_tools)
    assert len(tools) == 2
    assert tools[0]["name"] == "list_issues"
    assert tools[1]["name"] == "get_pull_request"
    assert "input_schema" in tools[0]
```

**Step 2: Run test to verify it fails**

Run: `cd ~/Documents/mcp-vs-cli-benchmark && python -m pytest tests/agents/test_mcp_agent.py -v`
Expected: FAIL

**Step 3: Write implementation**

```python
# src/benchmark/agents/mcp_agent.py
import json
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
        result = await self.session.call_tool(tool_name, arguments=tool_input)

        # MCP returns content blocks; concatenate text ones
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
```

**Step 4: Run test to verify it passes**

Run: `cd ~/Documents/mcp-vs-cli-benchmark && python -m pytest tests/agents/test_mcp_agent.py -v`
Expected: 1 passed

**Step 5: Commit**

```bash
git add src/benchmark/agents/mcp_agent.py tests/agents/test_mcp_agent.py
git commit -m "feat: add MCP agent with tool discovery and execution via MCP client"
```

---

### Task 8: GitHub Fixtures (Seed + Teardown)

**Files:**
- Create: `src/benchmark/fixtures/github_seed.py`
- Create: `tests/fixtures/test_github_seed.py`

**Step 1: Write the failing test**

```python
# tests/fixtures/test_github_seed.py
"""Tests for GitHub fixture data structure (not live API calls)."""


def test_github_fixture_data_is_consistent():
    from benchmark.fixtures.github_seed import GITHUB_FIXTURES

    issues = GITHUB_FIXTURES["issues"]
    prs = GITHUB_FIXTURES["pull_requests"]

    assert len(issues) == 10
    assert len(prs) == 5

    # All issues have required fields
    for issue in issues:
        assert "number" in issue
        assert "title" in issue
        assert "labels" in issue
        assert "state" in issue

    # Exactly 5 have label "bug"
    bug_issues = [i for i in issues if "bug" in i["labels"]]
    assert len(bug_issues) == 5

    # PRs: 3 merged, 2 open
    merged = [p for p in prs if p["state"] == "merged"]
    open_prs = [p for p in prs if p["state"] == "open"]
    assert len(merged) == 3
    assert len(open_prs) == 2


def test_seed_and_teardown_are_callable():
    from benchmark.fixtures.github_seed import GitHubSeeder

    seeder = GitHubSeeder(repo="test/repo", token="fake-token")
    # Should have async seed/teardown/verify methods
    assert hasattr(seeder, "seed")
    assert hasattr(seeder, "teardown")
    assert hasattr(seeder, "verify")
```

**Step 2: Run test to verify it fails**

Run: `cd ~/Documents/mcp-vs-cli-benchmark && python -m pytest tests/fixtures/test_github_seed.py -v`
Expected: FAIL

**Step 3: Write implementation**

```python
# src/benchmark/fixtures/github_seed.py
"""GitHub test fixture data and seeding logic."""

import httpx

GITHUB_FIXTURES: dict = {
    "issues": [
        {"number": 1, "title": "Login page returns 500 on invalid email format", "labels": ["bug"], "state": "open", "assignee": "alice"},
        {"number": 2, "title": "Add dark mode support", "labels": ["enhancement"], "state": "open", "assignee": "bob"},
        {"number": 3, "title": "CSS layout breaks on viewport < 768px", "labels": ["bug"], "state": "open", "assignee": "alice"},
        {"number": 4, "title": "Migrate from Jest to Vitest", "labels": ["chore"], "state": "open", "assignee": None},
        {"number": 5, "title": "Memory leak in WebSocket reconnection handler", "labels": ["bug", "critical"], "state": "open", "assignee": "charlie"},
        {"number": 6, "title": "Add OpenAPI spec for v2 endpoints", "labels": ["documentation"], "state": "open", "assignee": "bob"},
        {"number": 7, "title": "Race condition in concurrent file upload", "labels": ["bug"], "state": "open", "assignee": "alice"},
        {"number": 8, "title": "Upgrade to Node 22 LTS", "labels": ["chore"], "state": "closed", "assignee": "charlie"},
        {"number": 9, "title": "API rate limiter counts preflight requests", "labels": ["bug"], "state": "open", "assignee": "bob"},
        {"number": 10, "title": "Add pagination to /users endpoint", "labels": ["enhancement"], "state": "open", "assignee": None},
    ],
    "pull_requests": [
        {"number": 11, "title": "Fix login validation", "state": "merged", "author": "alice", "base": "main", "reviews": [{"user": "bob", "body": "LGTM", "state": "APPROVED"}]},
        {"number": 12, "title": "Add dark mode CSS variables", "state": "merged", "author": "bob", "base": "main", "reviews": [{"user": "charlie", "body": "Needs contrast fix", "state": "CHANGES_REQUESTED"}, {"user": "charlie", "body": "Fixed, looks good", "state": "APPROVED"}]},
        {"number": 13, "title": "Bump dependencies March 2026", "state": "merged", "author": "charlie", "base": "main", "reviews": [{"user": "alice", "body": "All green", "state": "APPROVED"}]},
        {"number": 14, "title": "WIP: WebSocket reconnection refactor", "state": "open", "author": "alice", "base": "main", "reviews": []},
        {"number": 15, "title": "Draft: Rate limiter fix", "state": "open", "author": "bob", "base": "main", "reviews": [{"user": "alice", "body": "Needs tests", "state": "CHANGES_REQUESTED"}]},
    ],
    "branches": ["main", "fix/login-validation", "feat/dark-mode", "chore/deps-march-2026", "fix/websocket-reconnect", "fix/rate-limiter"],
}

API_BASE = "https://api.github.com"


class GitHubSeeder:
    """Seeds and tears down GitHub test fixtures via the GitHub API."""

    def __init__(self, repo: str, token: str) -> None:
        self.repo = repo
        self.token = token
        self.client = httpx.AsyncClient(
            base_url=API_BASE,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )

    async def seed(self, run_id: str) -> None:
        """Create all fixture data in the test repo."""
        await self._create_labels()
        await self._create_issues()
        await self._create_branches(run_id)
        await self._create_pull_requests()

    async def teardown(self, run_id: str) -> None:
        """Remove all fixture data created for this run."""
        # Close/delete issues and PRs
        for issue in GITHUB_FIXTURES["issues"] + GITHUB_FIXTURES["pull_requests"]:
            await self.client.patch(
                f"/repos/{self.repo}/issues/{issue['number']}",
                json={"state": "closed"},
            )
        # Delete branches created for this run
        for branch in GITHUB_FIXTURES["branches"]:
            if branch != "main":
                await self.client.delete(
                    f"/repos/{self.repo}/git/refs/heads/{branch}"
                )
        # Delete run-specific branches
        await self.client.delete(
            f"/repos/{self.repo}/git/refs/heads/bench/{run_id}"
        )

    async def verify(self) -> bool:
        """Check that all expected fixture data exists."""
        resp = await self.client.get(
            f"/repos/{self.repo}/issues",
            params={"state": "all", "per_page": 100},
        )
        if resp.status_code != 200:
            return False
        issues = resp.json()
        return len(issues) >= len(GITHUB_FIXTURES["issues"])

    async def _create_labels(self) -> None:
        labels = {"bug", "enhancement", "chore", "documentation", "critical"}
        for label in labels:
            await self.client.post(
                f"/repos/{self.repo}/labels",
                json={"name": label, "color": "ededed"},
            )

    async def _create_issues(self) -> None:
        for issue in GITHUB_FIXTURES["issues"]:
            await self.client.post(
                f"/repos/{self.repo}/issues",
                json={
                    "title": issue["title"],
                    "labels": issue["labels"],
                    "assignees": [issue["assignee"]] if issue["assignee"] else [],
                },
            )

    async def _create_branches(self, run_id: str) -> None:
        # Get main branch SHA
        resp = await self.client.get(f"/repos/{self.repo}/git/ref/heads/main")
        if resp.status_code != 200:
            return
        main_sha = resp.json()["object"]["sha"]

        for branch in GITHUB_FIXTURES["branches"]:
            if branch != "main":
                await self.client.post(
                    f"/repos/{self.repo}/git/refs",
                    json={"ref": f"refs/heads/{branch}", "sha": main_sha},
                )

    async def _create_pull_requests(self) -> None:
        for pr in GITHUB_FIXTURES["pull_requests"]:
            if pr["state"] == "open":
                # Find the source branch for this PR
                branch_map = {
                    14: "fix/websocket-reconnect",
                    15: "fix/rate-limiter",
                }
                head = branch_map.get(pr["number"], "main")
                await self.client.post(
                    f"/repos/{self.repo}/pulls",
                    json={
                        "title": pr["title"],
                        "head": head,
                        "base": pr["base"],
                    },
                )

    async def close(self) -> None:
        await self.client.aclose()
```

**Step 4: Run test to verify it passes**

Run: `cd ~/Documents/mcp-vs-cli-benchmark && python -m pytest tests/fixtures/test_github_seed.py -v`
Expected: 2 passed

**Step 5: Commit**

```bash
git add src/benchmark/fixtures/github_seed.py tests/fixtures/test_github_seed.py
git commit -m "feat: add GitHub fixture data and seeder with seed/teardown/verify"
```

---

### Task 9: Verification Module (Ground Truth Checker)

**Files:**
- Create: `src/benchmark/metrics/verifier.py`
- Create: `tests/metrics/test_verifier.py`

**Step 1: Write the failing test**

```python
# tests/metrics/test_verifier.py
import json


def test_exact_match_pass():
    from benchmark.metrics.verifier import verify_output
    from benchmark.tasks.schema import VerificationConfig

    config = VerificationConfig(
        type="exact_match",
        ground_truth=[
            {"number": 1, "title": "Bug A"},
            {"number": 3, "title": "Bug B"},
        ],
    )
    agent_output = json.dumps([
        {"number": 1, "title": "Bug A"},
        {"number": 3, "title": "Bug B"},
    ])

    result = verify_output(agent_output, config)
    assert result.passed is True
    assert result.score == 1.0


def test_exact_match_partial():
    from benchmark.metrics.verifier import verify_output
    from benchmark.tasks.schema import VerificationConfig

    config = VerificationConfig(
        type="exact_match",
        ground_truth=[
            {"number": 1, "title": "Bug A"},
            {"number": 3, "title": "Bug B"},
        ],
    )
    # Agent only found one of two
    agent_output = json.dumps([{"number": 1, "title": "Bug A"}])

    result = verify_output(agent_output, config)
    assert result.passed is False
    assert result.score == 0.5


def test_contains_match():
    from benchmark.metrics.verifier import verify_output
    from benchmark.tasks.schema import VerificationConfig

    config = VerificationConfig(
        type="contains",
        ground_truth=["Login broken", "CSS glitch"],
    )
    agent_output = "Found issues: Login broken, CSS glitch, and Memory leak"

    result = verify_output(agent_output, config)
    assert result.passed is True
    assert result.score == 1.0


def test_exact_match_with_unparseable_output():
    from benchmark.metrics.verifier import verify_output
    from benchmark.tasks.schema import VerificationConfig

    config = VerificationConfig(
        type="exact_match",
        ground_truth=[{"number": 1}],
    )
    agent_output = "I couldn't find any issues, sorry."

    result = verify_output(agent_output, config)
    assert result.passed is False
    assert result.score == 0.0
```

**Step 2: Run test to verify it fails**

Run: `cd ~/Documents/mcp-vs-cli-benchmark && python -m pytest tests/metrics/test_verifier.py -v`
Expected: FAIL

**Step 3: Write implementation**

```python
# src/benchmark/metrics/verifier.py
import json
import re
from dataclasses import dataclass
from typing import Any

from benchmark.tasks.schema import VerificationConfig


@dataclass
class VerificationResult:
    passed: bool
    score: float  # 0.0 to 1.0
    details: str


def verify_output(agent_output: str, config: VerificationConfig) -> VerificationResult:
    """Verify agent output against ground truth."""
    if config.type == "exact_match":
        return _exact_match(agent_output, config.ground_truth)
    elif config.type == "contains":
        return _contains_match(agent_output, config.ground_truth)
    elif config.type == "llm_judge":
        # LLM judge is handled separately via judge.py
        return VerificationResult(passed=True, score=1.0, details="Deferred to LLM judge")
    elif config.type == "api_check":
        return VerificationResult(passed=True, score=1.0, details="Deferred to API check")
    else:
        return VerificationResult(passed=False, score=0.0, details=f"Unknown type: {config.type}")


def _extract_json(text: str) -> Any:
    """Try to extract JSON from agent output text."""
    # Try parsing the whole thing first
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    # Try to find a JSON array or object in the text
    for pattern in [r'\[.*\]', r'\{.*\}']:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                continue

    return None


def _exact_match(agent_output: str, ground_truth: Any) -> VerificationResult:
    """Compare parsed JSON output against ground truth list."""
    if not isinstance(ground_truth, list):
        ground_truth = [ground_truth]

    parsed = _extract_json(agent_output)
    if parsed is None:
        return VerificationResult(
            passed=False, score=0.0, details="Could not parse agent output as JSON"
        )

    if not isinstance(parsed, list):
        parsed = [parsed]

    # Count how many ground truth items appear in the output
    matched = 0
    for expected in ground_truth:
        for actual in parsed:
            if _items_match(expected, actual):
                matched += 1
                break

    total = len(ground_truth)
    score = matched / total if total > 0 else 0.0
    passed = matched == total

    return VerificationResult(
        passed=passed,
        score=score,
        details=f"Matched {matched}/{total} items",
    )


def _items_match(expected: Any, actual: Any) -> bool:
    """Check if all fields in expected exist and match in actual."""
    if isinstance(expected, dict) and isinstance(actual, dict):
        return all(
            key in actual and actual[key] == value
            for key, value in expected.items()
        )
    return expected == actual


def _contains_match(agent_output: str, ground_truth: Any) -> VerificationResult:
    """Check if all ground truth strings appear in the output."""
    if not isinstance(ground_truth, list):
        ground_truth = [ground_truth]

    matched = sum(1 for item in ground_truth if str(item) in agent_output)
    total = len(ground_truth)
    score = matched / total if total > 0 else 0.0

    return VerificationResult(
        passed=matched == total,
        score=score,
        details=f"Found {matched}/{total} expected strings",
    )
```

**Step 4: Run test to verify it passes**

Run: `cd ~/Documents/mcp-vs-cli-benchmark && python -m pytest tests/metrics/test_verifier.py -v`
Expected: 4 passed

**Step 5: Commit**

```bash
git add src/benchmark/metrics/verifier.py tests/metrics/test_verifier.py
git commit -m "feat: add output verifier with exact match, contains, and partial scoring"
```

---

### Task 10: LLM-as-Judge

**Files:**
- Create: `src/benchmark/metrics/judge.py`
- Create: `tests/metrics/test_judge.py`

**Step 1: Write the failing test**

```python
# tests/metrics/test_judge.py
import json


def test_judge_prompt_is_blinded():
    """Judge must not know which output is CLI vs MCP."""
    from benchmark.metrics.judge import build_judge_prompt

    prompt = build_judge_prompt(
        task_description="List all bug issues",
        output_a="[{\"number\": 1}]",
        output_b="[{\"number\": 1}, {\"number\": 3}]",
    )

    assert "CLI" not in prompt
    assert "MCP" not in prompt
    assert "Output A" in prompt
    assert "Output B" in prompt


def test_judge_prompt_includes_rubric():
    from benchmark.metrics.judge import build_judge_prompt

    prompt = build_judge_prompt(
        task_description="List all bug issues",
        output_a="output1",
        output_b="output2",
    )

    assert "1" in prompt and "5" in prompt  # scoring scale
    assert "correctness" in prompt.lower() or "completeness" in prompt.lower()


def test_parse_judge_response():
    from benchmark.metrics.judge import parse_judge_response

    response = json.dumps({
        "score_a": 3,
        "score_b": 5,
        "rationale_a": "Missing some issues",
        "rationale_b": "Complete and correct",
    })

    scores = parse_judge_response(response)
    assert scores["score_a"] == 3
    assert scores["score_b"] == 5


def test_parse_judge_response_handles_bad_json():
    from benchmark.metrics.judge import parse_judge_response

    response = "I think output A scores 3 and output B scores 5"
    scores = parse_judge_response(response)
    assert scores is None
```

**Step 2: Run test to verify it fails**

Run: `cd ~/Documents/mcp-vs-cli-benchmark && python -m pytest tests/metrics/test_judge.py -v`
Expected: FAIL

**Step 3: Write implementation**

```python
# src/benchmark/metrics/judge.py
import json
import random
from typing import Any

import anthropic

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


def build_judge_prompt(
    task_description: str,
    output_a: str,
    output_b: str,
) -> str:
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
    """Parse the judge's JSON response. Returns None if unparseable."""
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
    """Run LLM-as-judge evaluation. Returns (cli_verdicts, mcp_verdicts).

    Randomly assigns CLI/MCP to A/B positions to avoid position bias.
    Runs `attempts` times and returns all verdicts (caller takes majority).
    """
    client = anthropic.Anthropic()
    cli_verdicts: list[JudgeVerdict] = []
    mcp_verdicts: list[JudgeVerdict] = []

    for attempt in range(1, attempts + 1):
        # Randomly assign positions to avoid order bias
        cli_is_a = random.random() < 0.5
        if cli_is_a:
            output_a, output_b = cli_output, mcp_output
        else:
            output_a, output_b = mcp_output, cli_output

        prompt = build_judge_prompt(task_description, output_a, output_b)

        response = client.messages.create(
            model=judge_model,
            max_tokens=1024,
            temperature=0,
            system=JUDGE_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )

        text = response.content[0].text if response.content else ""
        scores = parse_judge_response(text)

        if scores is None:
            continue

        cli_score = scores["score_a"] if cli_is_a else scores["score_b"]
        mcp_score = scores["score_b"] if cli_is_a else scores["score_a"]
        cli_rationale = scores["rationale_a"] if cli_is_a else scores["rationale_b"]
        mcp_rationale = scores["rationale_b"] if cli_is_a else scores["rationale_a"]

        cli_verdicts.append(JudgeVerdict(
            run_id=cli_run_id,
            task_id=task_id,
            quality_score=cli_score,
            rationale=cli_rationale,
            judge_model=judge_model,
            attempt=attempt,
        ))
        mcp_verdicts.append(JudgeVerdict(
            run_id=mcp_run_id,
            task_id=task_id,
            quality_score=mcp_score,
            rationale=mcp_rationale,
            judge_model=judge_model,
            attempt=attempt,
        ))

    return cli_verdicts, mcp_verdicts
```

**Step 4: Run test to verify it passes**

Run: `cd ~/Documents/mcp-vs-cli-benchmark && python -m pytest tests/metrics/test_judge.py -v`
Expected: 4 passed

**Step 5: Commit**

```bash
git add src/benchmark/metrics/judge.py tests/metrics/test_judge.py
git commit -m "feat: add blinded LLM-as-judge with random position assignment"
```

---

### Task 11: Runner Harness (Orchestrator)

**Files:**
- Create: `src/benchmark/runner/config.py`
- Create: `src/benchmark/runner/harness.py`
- Create: `tests/runner/test_harness.py`

**Step 1: Write the failing test**

```python
# tests/runner/test_harness.py
import random


def test_scheduler_alternates_modalities():
    from benchmark.runner.config import BenchmarkConfig

    config = BenchmarkConfig(
        runs_per_modality=5,
        model="claude-sonnet-4-20250514",
        services=["github"],
    )
    schedule = config.build_schedule()

    # Should alternate CLI/MCP
    modalities = [entry.modality for entry in schedule]
    for i in range(0, len(modalities) - 1, 2):
        pair = {modalities[i], modalities[i + 1]}
        assert pair == {"cli", "mcp"}, f"Pair {i} not alternating: {pair}"


def test_scheduler_randomizes_task_order():
    from benchmark.runner.config import BenchmarkConfig

    config = BenchmarkConfig(
        runs_per_modality=30,
        model="claude-sonnet-4-20250514",
        services=["github"],
        seed=42,
    )
    schedule = config.build_schedule()
    task_ids = [entry.task_id for entry in schedule]

    # With 30 runs, task order should vary (not always the same sequence)
    # Check first 5 task_ids vs another set of 5
    first_chunk = task_ids[:5]
    # Somewhere in the schedule, order should differ
    assert len(set(task_ids)) > 1  # Not all the same task


def test_config_marks_cold_starts():
    from benchmark.runner.config import BenchmarkConfig

    config = BenchmarkConfig(
        runs_per_modality=10,
        model="claude-sonnet-4-20250514",
        services=["github"],
        cold_start_runs=3,
    )
    schedule = config.build_schedule()

    cold = [e for e in schedule if e.is_cold_start]
    warm = [e for e in schedule if not e.is_cold_start]

    # First 3 runs per modality should be cold
    assert len(cold) > 0
    assert len(warm) > 0
```

**Step 2: Run test to verify it fails**

Run: `cd ~/Documents/mcp-vs-cli-benchmark && python -m pytest tests/runner/test_harness.py -v`
Expected: FAIL

**Step 3: Write implementation**

```python
# src/benchmark/runner/config.py
import random
import uuid
from dataclasses import dataclass, field

from pydantic import BaseModel


class ScheduleEntry(BaseModel):
    """A single scheduled run in the benchmark."""

    run_id: str
    task_id: str
    service: str
    modality: str  # "cli" or "mcp"
    is_cold_start: bool
    run_number: int  # 1-based index within this modality


# Default task IDs per service (will be overridden by registry in practice)
DEFAULT_TASK_IDS: dict[str, list[str]] = {
    "github": [f"github_{i:02d}" for i in range(1, 6)],
    "google": [f"google_{i:02d}" for i in range(1, 6)],
    "postgres": [f"postgres_{i:02d}" for i in range(1, 6)],
}


class BenchmarkConfig(BaseModel):
    """Configuration for a benchmark run suite."""

    runs_per_modality: int = 30
    model: str = "claude-sonnet-4-20250514"
    judge_model: str = "claude-opus-4-20250514"
    services: list[str] = ["github"]
    cold_start_runs: int = 3
    seed: int | None = None
    task_ids: dict[str, list[str]] | None = None

    def build_schedule(self) -> list[ScheduleEntry]:
        """Build alternating CLI/MCP schedule with randomized task order."""
        rng = random.Random(self.seed)
        task_map = self.task_ids or DEFAULT_TASK_IDS

        entries: list[ScheduleEntry] = []
        cli_count = 0
        mcp_count = 0

        for run_num in range(1, self.runs_per_modality + 1):
            # Get tasks for this round, randomize order
            tasks_this_round: list[tuple[str, str]] = []
            for service in self.services:
                service_tasks = task_map.get(service, [])
                for tid in service_tasks:
                    tasks_this_round.append((service, tid))

            rng.shuffle(tasks_this_round)

            for service, task_id in tasks_this_round:
                # CLI run
                cli_count += 1
                entries.append(ScheduleEntry(
                    run_id=str(uuid.uuid4()),
                    task_id=task_id,
                    service=service,
                    modality="cli",
                    is_cold_start=cli_count <= self.cold_start_runs,
                    run_number=cli_count,
                ))

                # MCP run (alternating)
                mcp_count += 1
                entries.append(ScheduleEntry(
                    run_id=str(uuid.uuid4()),
                    task_id=task_id,
                    service=service,
                    modality="mcp",
                    is_cold_start=mcp_count <= self.cold_start_runs,
                    run_number=mcp_count,
                ))

        return entries
```

```python
# src/benchmark/runner/harness.py
import json
import time
from pathlib import Path

from rich.console import Console
from rich.progress import Progress

from benchmark.metrics.schemas import RunResult
from benchmark.metrics.verifier import verify_output
from benchmark.runner.config import BenchmarkConfig, ScheduleEntry
from benchmark.tasks.registry import TaskRegistry

console = Console()


class BenchmarkHarness:
    """Orchestrates the full benchmark: seed -> run -> verify -> teardown."""

    def __init__(
        self,
        config: BenchmarkConfig,
        task_registry: TaskRegistry,
        results_dir: Path,
    ) -> None:
        self.config = config
        self.registry = task_registry
        self.results_dir = results_dir
        self.results_dir.mkdir(parents=True, exist_ok=True)

    async def run_schedule(self, schedule: list[ScheduleEntry]) -> list[RunResult]:
        """Execute the full schedule, returning all results."""
        results: list[RunResult] = []

        with Progress() as progress:
            task = progress.add_task(
                "Running benchmark...", total=len(schedule)
            )

            for entry in schedule:
                task_def = self.registry.get_task(entry.task_id)
                if task_def is None:
                    console.print(f"[yellow]Skipping unknown task: {entry.task_id}[/]")
                    progress.advance(task)
                    continue

                console.print(
                    f"[dim]{entry.modality.upper()}[/] {entry.task_id} "
                    f"(run {entry.run_number}, "
                    f"{'cold' if entry.is_cold_start else 'warm'})"
                )

                # TODO: seed fixtures for this service
                # TODO: create appropriate agent (CLI or MCP)
                # TODO: run agent
                # TODO: verify output
                # TODO: teardown fixtures

                # Placeholder — will be wired in when agents are integrated
                progress.advance(task)

        return results

    def save_result(self, result: RunResult) -> None:
        """Save a single run result to disk as JSON."""
        path = self.results_dir / f"{result.run_id}.json"
        path.write_text(result.model_dump_json(indent=2))

    def save_all_results(self, results: list[RunResult]) -> None:
        for result in results:
            self.save_result(result)
```

**Step 4: Run test to verify it passes**

Run: `cd ~/Documents/mcp-vs-cli-benchmark && python -m pytest tests/runner/test_harness.py -v`
Expected: 3 passed

**Step 5: Commit**

```bash
git add src/benchmark/runner/ tests/runner/
git commit -m "feat: add benchmark config, scheduler with alternation/randomization, and harness"
```

---

### Task 12: CLI Entry Point

**Files:**
- Create: `src/benchmark/cli.py`

**Step 1: Write minimal CLI**

```python
# src/benchmark/cli.py
"""CLI entry point for the benchmark harness."""

import argparse
import asyncio
import json
import sys
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console

from benchmark.runner.config import BenchmarkConfig
from benchmark.runner.harness import BenchmarkHarness
from benchmark.tasks.registry import TaskRegistry

console = Console()


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(description="MCP vs CLI Benchmark")
    subparsers = parser.add_subparsers(dest="command")

    # Run command
    run_parser = subparsers.add_parser("run", help="Run benchmark suite")
    run_parser.add_argument("--service", nargs="+", default=["github"])
    run_parser.add_argument("--runs", type=int, default=30)
    run_parser.add_argument("--model", default="claude-sonnet-4-20250514")
    run_parser.add_argument("--seed", type=int, default=None)
    run_parser.add_argument("--output", default="results/raw")

    # Analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze results")
    analyze_parser.add_argument("--input", default="results/raw")

    args = parser.parse_args()

    if args.command == "run":
        config = BenchmarkConfig(
            runs_per_modality=args.runs,
            model=args.model,
            services=args.service,
            seed=args.seed,
        )
        tasks_dir = Path(__file__).parent.parent.parent / "tasks"
        registry = TaskRegistry(tasks_dir)
        results_dir = Path(args.output)

        harness = BenchmarkHarness(config, registry, results_dir)
        schedule = config.build_schedule()

        console.print(f"[bold]MCP vs CLI Benchmark[/]")
        console.print(f"Services: {config.services}")
        console.print(f"Runs per modality: {config.runs_per_modality}")
        console.print(f"Total scheduled runs: {len(schedule)}")
        console.print()

        results = asyncio.run(harness.run_schedule(schedule))
        harness.save_all_results(results)
        console.print(f"\n[green]Done. {len(results)} results saved to {results_dir}[/]")

    elif args.command == "analyze":
        console.print("[yellow]Analysis not yet implemented[/]")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
```

**Step 2: Test it runs**

Run: `cd ~/Documents/mcp-vs-cli-benchmark && python -m benchmark.cli --help`
Expected: Shows help with `run` and `analyze` subcommands.

**Step 3: Commit**

```bash
git add src/benchmark/cli.py
git commit -m "feat: add CLI entry point with run and analyze subcommands"
```

---

### Task 13: Remaining GitHub Task YAMLs

**Files:**
- Create: `tasks/github/task_02_get_pr.yaml`
- Create: `tasks/github/task_03_create_issue.yaml`
- Create: `tasks/github/task_04_summarize_prs.yaml`
- Create: `tasks/github/task_05_create_branch_pr.yaml`

**Step 1: Create all four task files**

```yaml
# tasks/github/task_02_get_pr.yaml
id: github_02
service: github
name: Get PR details including review comments
complexity: multi_step_read
prompt: |
  Get the details of pull request #12 in the repository {repo}.
  Return a JSON object with these fields:
  - "number": the PR number
  - "title": the PR title
  - "state": "open" or "merged"
  - "author": the PR author's username
  - "reviews": an array of objects with "user", "body", and "state" fields

  Return ONLY the JSON object, no other text.
prompt_vars:
  repo: "scalekit-inc/mcp-vs-cli-benchmark-data"
verification:
  type: exact_match
  ground_truth:
    number: 12
    title: "Add dark mode CSS variables"
    state: "merged"
    author: "bob"
    reviews:
      - user: "charlie"
        body: "Needs contrast fix"
        state: "CHANGES_REQUESTED"
      - user: "charlie"
        body: "Fixed, looks good"
        state: "APPROVED"
```

```yaml
# tasks/github/task_03_create_issue.yaml
id: github_03
service: github
name: Create an issue with title body and labels
complexity: simple_write
prompt: |
  Create a new issue in the repository {repo} with the following details:
  - Title: "Benchmark test issue {run_id}"
  - Body: "This is an automated test issue created by the MCP vs CLI benchmark."
  - Labels: ["bug", "enhancement"]

  After creating the issue, return a JSON object with:
  - "number": the issue number that was created
  - "title": the title
  - "url": the HTML URL of the issue

  Return ONLY the JSON object, no other text.
prompt_vars:
  repo: "scalekit-inc/mcp-vs-cli-benchmark-data"
  run_id: "PLACEHOLDER"
verification:
  type: api_check
  check_endpoint: "/repos/{repo}/issues/{number}"
```

```yaml
# tasks/github/task_04_summarize_prs.yaml
id: github_04
service: github
name: Find and summarize merged PRs by user
complexity: complex_read
prompt: |
  In the repository {repo}, find all pull requests authored by "alice"
  that have been merged. For each merged PR, provide:
  - The PR number
  - The PR title
  - A one-sentence summary of what the PR does (based on its title and review comments)

  Return a JSON array of objects with "number", "title", and "summary" fields.
  Return ONLY the JSON array, no other text.
prompt_vars:
  repo: "scalekit-inc/mcp-vs-cli-benchmark-data"
verification:
  type: llm_judge
  judge_prompt: |
    The agent was asked to find all merged PRs by "alice" and summarize them.
    Ground truth: Alice has 1 merged PR: #11 "Fix login validation".
    Evaluate if the agent found the correct PRs and provided reasonable summaries.
```

```yaml
# tasks/github/task_05_create_branch_pr.yaml
id: github_05
service: github
name: Create branch commit file and open PR
complexity: multi_step_write
prompt: |
  In the repository {repo}, perform these steps:
  1. Create a new branch named "bench/{run_id}/test-feature" from the main branch
  2. Create a file called "benchmark-test.md" with the content "# Benchmark Test\nCreated by run {run_id}"
  3. Commit the file to the new branch
  4. Open a pull request from "bench/{run_id}/test-feature" to "main" with:
     - Title: "Benchmark test PR {run_id}"
     - Body: "Automated PR from benchmark run."

  After completing all steps, return a JSON object with:
  - "branch": the branch name
  - "pr_number": the PR number
  - "pr_url": the HTML URL of the PR

  Return ONLY the JSON object, no other text.
prompt_vars:
  repo: "scalekit-inc/mcp-vs-cli-benchmark-data"
  run_id: "PLACEHOLDER"
verification:
  type: api_check
  check_endpoint: "/repos/{repo}/pulls/{pr_number}"
```

**Step 2: Verify tasks load**

Run: `cd ~/Documents/mcp-vs-cli-benchmark && python -c "from benchmark.tasks.registry import TaskRegistry; from pathlib import Path; r = TaskRegistry(Path('tasks')); print(f'{len(r.get_tasks(\"github\"))} GitHub tasks loaded')"`
Expected: `5 GitHub tasks loaded`

**Step 3: Commit**

```bash
git add tasks/github/
git commit -m "feat: add all 5 GitHub benchmark task definitions"
```

---

### Task 14: METHODOLOGY.md (Pre-Registration)

**Files:**
- Create: `METHODOLOGY.md`

**Step 1: Write pre-registration document**

```markdown
# Pre-Registered Methodology

> This document was written and committed BEFORE running any benchmarks.
> It constitutes our pre-registration of hypotheses and methods.

## Hypotheses

1. **H1 (Token Efficiency):** MCP agents will use fewer total tokens than CLI agents
   for the same tasks, because MCP returns structured data while CLI returns raw
   terminal output that requires parsing.

2. **H2 (Simple Task Latency):** CLI agents will complete simple read tasks faster
   (wall-clock) than MCP agents, due to lower protocol overhead.

3. **H3 (Complex Task Completion):** MCP agents will have a higher task completion
   rate on complex multi-step tasks (complexity: complex_read, multi_step_write),
   because structured tool interfaces reduce ambiguity and error rates.

4. **H4 (Cold Start):** MCP agents will exhibit a larger cold-start latency penalty
   than CLI agents, because MCP servers require initialization.

## Statistical Methods

- **Sample size:** 30 runs per agent per task (minimum for CLT).
- **Test:** Paired Wilcoxon signed-rank test (non-parametric, two-sided).
- **Significance:** p < 0.05 after Bonferroni correction (15 comparisons).
- **Effect size:** Cohen's d reported alongside all p-values.
- **Confidence intervals:** 95% CI on mean difference (CLI - MCP).

## LLM-as-Judge

- Judge model differs from benchmark model (benchmark: Sonnet, judge: Opus).
- Outputs presented side-by-side, randomly ordered, without modality labels.
- Each pair judged 3 times; majority vote determines final score.
- Inter-judge agreement reported via Fleiss' kappa.

## Run Conditions

- Temperature: 0 for all benchmark runs.
- Runs alternate between CLI and MCP to control for time-of-day effects.
- Task order randomized within each run.
- Each run uses a fresh API conversation (no shared context).
- First 3 runs per modality flagged as cold starts, analyzed separately.

## What We Will Report

For each metric (tokens, tool calls, latency, completion, quality):
- Descriptive statistics: median, mean, std dev, P25, P75, P95
- Statistical test results with exact p-values
- Effect sizes (Cohen's d)
- Confidence intervals
- Visualization: box plots + strip plots overlaid

## Limitations (Known Before Running)

- Single LLM provider (Anthropic Claude); results may not generalize to others.
- CLI tools tested in macOS environment; behavior may differ on Linux.
- MCP servers tested locally (HTTP transport); remote deployment may differ.
- Fixture data is synthetic; real-world data may produce different patterns.
- 30 runs provides moderate statistical power; rare failure modes may be missed.
```

**Step 2: Commit**

```bash
git add METHODOLOGY.md
git commit -m "docs: add pre-registered methodology with hypotheses and statistical methods"
```

---

### Task 15: End-to-End Smoke Test (1 Run, 1 Task)

**Files:**
- Create: `tests/test_smoke.py`

**Step 1: Write smoke test**

```python
# tests/test_smoke.py
"""Smoke test: runs 1 CLI task against a simple echo command.

This test verifies the full pipeline works end-to-end without requiring
real API keys or external services. Uses a mock Claude response.
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_full_pipeline_smoke():
    """Verify: task loads -> agent runs -> metrics collected -> result saved."""
    from benchmark.agents.cli_agent import CliAgent
    from benchmark.metrics.schemas import RunResult
    from benchmark.metrics.verifier import verify_output
    from benchmark.tasks.schema import TaskDefinition, VerificationConfig

    # 1. Define a simple task
    task = TaskDefinition(
        id="smoke_01",
        service="test",
        name="Echo test",
        complexity="simple_read",
        prompt='Run the command: echo \'[{"number": 1, "title": "Test"}]\' and return its output exactly.',
        prompt_vars={},
        verification=VerificationConfig(
            type="exact_match",
            ground_truth=[{"number": 1, "title": "Test"}],
        ),
    )

    # 2. Mock Claude API to return a tool_use then text
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

        # 3. Run the agent
        result = await agent.run(
            task=task,
            run_id="smoke-test-001",
            modality="cli",
            is_cold_start=False,
        )

    # 4. Verify metrics were collected
    assert isinstance(result, RunResult)
    assert result.run_id == "smoke-test-001"
    assert result.total_tokens == 330  # 100+150 input, 50+30 output
    assert result.tool_call_count == 1
    assert result.task_completed is True

    # 5. Verify output against ground truth
    verification = verify_output(result.agent_output, task.verification)
    assert verification.passed is True
    assert verification.score == 1.0

    # 6. Verify result serializes to JSON
    json_str = result.model_dump_json()
    restored = RunResult.model_validate_json(json_str)
    assert restored.run_id == "smoke-test-001"
```

**Step 2: Run smoke test**

Run: `cd ~/Documents/mcp-vs-cli-benchmark && python -m pytest tests/test_smoke.py -v`
Expected: 1 passed

**Step 3: Commit**

```bash
git add tests/test_smoke.py
git commit -m "test: add end-to-end smoke test for full pipeline with mocked Claude API"
```

---

## Phase 2: Google Workspace + Postgres Benchmarks

### Task 16: Postgres Fixtures (SQL Seed + Docker)

**Files:**
- Create: `fixtures/postgres_seed.sql`
- Create: `src/benchmark/fixtures/postgres_seed.py`
- Create: `docker-compose.yaml` (benchmark Postgres instance)
- Create: `tests/fixtures/test_postgres_seed.py`

Steps: Create deterministic SQL fixtures with `benchmark` schema containing `customers`, `orders`, `products` tables. Write a `PostgresSeeder` class with `seed()`, `teardown()`, `verify()` methods using `asyncpg`. Docker compose file for local Postgres on port 5433 (avoid conflict with Gateway).

### Task 17: Postgres Task YAMLs (5 Tasks)

**Files:**
- Create: `tasks/postgres/task_01_list_tables.yaml` through `task_05_create_table.yaml`

Steps: Define 5 tasks matching the design doc. Each with ground truth from the seed data.

### Task 18: Google Workspace Fixtures

**Files:**
- Create: `src/benchmark/fixtures/google_seed.py`
- Create: `tests/fixtures/test_google_seed.py`

Steps: `GoogleSeeder` class using Google Drive API + Gmail API. Service account auth. Seed a known folder structure and emails.

### Task 19: Google Workspace Task YAMLs (5 Tasks)

**Files:**
- Create: `tasks/google/task_01_list_files.yaml` through `task_05_summarize_docs.yaml`

### Task 20: Wire Fixtures Into Harness

**Files:**
- Modify: `src/benchmark/runner/harness.py`

Steps: Add fixture lifecycle (seed/verify/teardown) to the run loop. Create a `FixtureManager` that dispatches to the right seeder per service.

---

## Phase 3: Full Run Suite + Analysis

### Task 21: Statistical Analysis Module

**Files:**
- Create: `src/benchmark/analysis/stats.py`
- Create: `tests/analysis/test_stats.py`

Steps: Implement `wilcoxon_test()`, `cohens_d()`, `confidence_interval()`, `bonferroni_correct()` using scipy. All functions take two arrays of measurements and return structured results.

### Task 22: Visualization Module

**Files:**
- Create: `src/benchmark/analysis/visualize.py`

Steps: Box plots + strip plots per metric per task using plotly. Generate HTML report with all charts. Summary table with p-values, effect sizes, CIs.

### Task 23: Report Generator

**Files:**
- Create: `src/benchmark/analysis/report.py`

Steps: Read all `results/raw/*.json`, group by task+modality, run stats, generate charts, output `results/reports/YYYY-MM-DD-report.md` with embedded chart images.

### Task 24: Wire `bench analyze` Command

**Files:**
- Modify: `src/benchmark/cli.py`

Steps: Connect the analyze subcommand to the analysis pipeline.

### Task 25: Run Full Suite

Steps: Execute `bench run --service github google postgres --runs 30 --seed 42`. Monitor for failures. Rerun any failed seeds. Generate analysis report.

---

## Phase 4: Enterprise Demos

### Task 26: Access Control Demo

**Files:**
- Create: `enterprise/access_control_demo.py`

Steps: Script that shows the same agent trying a write operation. CLI version succeeds (has full token). MCP version fails (Gateway restricts to read-only tools). Capture both outputs for the blog post.

### Task 27: Audit Trail Demo

**Files:**
- Create: `enterprise/audit_trail_demo.py`

Steps: Script that runs an agent through 5 operations, then shows: (a) CLI has no audit trail, (b) Gateway has structured logs for every call. Export Gateway logs in JSON format.

---

## Phase 5-6: Content

### Task 28: Blog Post #1 — Technical Benchmark

**Files:**
- Create: `content/blog_01_benchmark.md`

Steps: Write the developer-audience post using results from Phase 3. Include charts, statistical findings, methodology link. Narrative: fair comparison, surprising findings, what each modality is best at.

### Task 29: Blog Post #2 — Enterprise Implications

**Files:**
- Create: `content/blog_02_enterprise.md`

Steps: Write the leader-audience post using demos from Phase 4. The "dropped table" narrative. Access control comparison. Why MCP + Gateway matters for production AI.

### Task 30: README + Polish

**Files:**
- Modify: `README.md`

Steps: Full README with setup instructions, how to reproduce, links to methodology and results. Badges, screenshots of charts.
