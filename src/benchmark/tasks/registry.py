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
