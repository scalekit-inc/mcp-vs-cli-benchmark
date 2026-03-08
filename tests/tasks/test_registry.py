"""Tests for task definition schema and registry."""

import textwrap
from pathlib import Path

import yaml

from benchmark.tasks.schema import TaskDefinition, VerificationConfig
from benchmark.tasks.registry import TaskRegistry


class TestTaskDefinition:
    """Tests for TaskDefinition model."""

    def test_loads_from_dict(self) -> None:
        """TaskDefinition loads from a dict (simulating YAML parse)."""
        data = {
            "id": "github_01",
            "service": "github",
            "name": "List open issues with label bug",
            "complexity": "simple_read",
            "prompt": "List all open issues in {repo}.",
            "prompt_vars": {"repo": "owner/repo"},
            "verification": {
                "type": "exact_match",
                "ground_truth": [{"number": 1, "title": "Bug"}],
            },
        }
        task = TaskDefinition.model_validate(data)
        assert task.id == "github_01"
        assert task.service == "github"
        assert task.complexity == "simple_read"
        assert task.verification.type == "exact_match"
        assert task.verification.ground_truth == [{"number": 1, "title": "Bug"}]

    def test_rendered_prompt_substitutes_variables(self) -> None:
        """rendered_prompt() substitutes variables correctly."""
        task = TaskDefinition(
            id="test_01",
            service="test",
            name="Test task",
            complexity="simple_read",
            prompt="List issues in {repo} with label {label}.",
            prompt_vars={"repo": "owner/repo", "label": "bug"},
            verification=VerificationConfig(type="exact_match", ground_truth=[]),
        )
        result = task.rendered_prompt()
        assert result == "List issues in owner/repo with label bug."

    def test_rendered_prompt_no_vars(self) -> None:
        """rendered_prompt() returns prompt unchanged when no vars."""
        task = TaskDefinition(
            id="test_02",
            service="test",
            name="Test task",
            complexity="simple_read",
            prompt="Do something simple.",
            verification=VerificationConfig(type="contains"),
        )
        assert task.rendered_prompt() == "Do something simple."

    def test_default_prompt_vars_empty(self) -> None:
        """prompt_vars defaults to empty dict."""
        task = TaskDefinition(
            id="test_03",
            service="test",
            name="Test",
            complexity="simple_write",
            prompt="Write something.",
            verification=VerificationConfig(type="llm_judge", judge_prompt="Is it good?"),
        )
        assert task.prompt_vars == {}


class TestTaskRegistry:
    """Tests for TaskRegistry."""

    def _make_task_yaml(self, tasks_dir: Path, service: str, filename: str, data: dict) -> None:
        """Helper to write a YAML task file."""
        service_dir = tasks_dir / service
        service_dir.mkdir(parents=True, exist_ok=True)
        with open(service_dir / filename, "w") as f:
            yaml.dump(data, f)

    def test_loads_tasks_from_temp_directory(self, tmp_path: Path) -> None:
        """TaskRegistry loads all tasks from a temp directory with YAML files."""
        self._make_task_yaml(tmp_path, "github", "task_01.yaml", {
            "id": "gh_01",
            "service": "github",
            "name": "Task one",
            "complexity": "simple_read",
            "prompt": "Do thing one.",
            "verification": {"type": "exact_match", "ground_truth": "result"},
        })
        registry = TaskRegistry(tmp_path)
        tasks = registry.get_tasks("github")
        assert len(tasks) == 1
        assert tasks[0].id == "gh_01"

    def test_get_all_tasks_across_services(self, tmp_path: Path) -> None:
        """get_all_tasks() returns tasks across multiple service directories."""
        self._make_task_yaml(tmp_path, "github", "task_01.yaml", {
            "id": "gh_01",
            "service": "github",
            "name": "GitHub task",
            "complexity": "simple_read",
            "prompt": "Do GitHub thing.",
            "verification": {"type": "exact_match"},
        })
        self._make_task_yaml(tmp_path, "slack", "task_01.yaml", {
            "id": "slack_01",
            "service": "slack",
            "name": "Slack task",
            "complexity": "simple_write",
            "prompt": "Do Slack thing.",
            "verification": {"type": "contains"},
        })
        registry = TaskRegistry(tmp_path)
        all_tasks = registry.get_all_tasks()
        assert len(all_tasks) == 2
        ids = {t.id for t in all_tasks}
        assert ids == {"gh_01", "slack_01"}

    def test_get_task_by_id(self, tmp_path: Path) -> None:
        """get_task() returns the correct task by ID."""
        self._make_task_yaml(tmp_path, "github", "task_01.yaml", {
            "id": "gh_01",
            "service": "github",
            "name": "First",
            "complexity": "simple_read",
            "prompt": "First task.",
            "verification": {"type": "exact_match"},
        })
        self._make_task_yaml(tmp_path, "github", "task_02.yaml", {
            "id": "gh_02",
            "service": "github",
            "name": "Second",
            "complexity": "complex_read",
            "prompt": "Second task.",
            "verification": {"type": "llm_judge", "judge_prompt": "Check it."},
        })
        registry = TaskRegistry(tmp_path)
        task = registry.get_task("gh_02")
        assert task is not None
        assert task.name == "Second"
        assert task.complexity == "complex_read"

    def test_get_task_returns_none_for_missing(self, tmp_path: Path) -> None:
        """get_task() returns None for a non-existent ID."""
        registry = TaskRegistry(tmp_path)
        assert registry.get_task("nonexistent") is None

    def test_get_tasks_returns_empty_for_unknown_service(self, tmp_path: Path) -> None:
        """get_tasks() returns empty list for unknown service."""
        registry = TaskRegistry(tmp_path)
        assert registry.get_tasks("unknown") == []
