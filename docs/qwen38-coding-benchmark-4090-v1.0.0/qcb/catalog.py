from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .util import load_json


@dataclass(frozen=True)
class Task:
    id: str
    title: str
    category: str
    language: str
    difficulty: int
    weight: float
    task_type: str
    task_dir: Path
    metadata: dict[str, Any]

    @property
    def prompt(self) -> str:
        return (self.task_dir / self.metadata.get("prompt_file", "prompt.md")).read_text(encoding="utf-8")

    @property
    def workspace_dir(self) -> Path:
        return self.task_dir / self.metadata.get("workspace_dir", "workspace")

    @property
    def verifier_path(self) -> Path:
        return self.task_dir / self.metadata.get("verifier", "hidden_tests/verify.py")


def load_task(root: str | Path, task_id: str) -> Task:
    task_dir = Path(root) / "tasks" / task_id
    metadata = load_json(task_dir / "task.json")
    return Task(
        id=metadata["id"],
        title=metadata["title"],
        category=metadata["category"],
        language=metadata["language"],
        difficulty=int(metadata["difficulty"]),
        weight=float(metadata.get("weight", 1.0)),
        task_type=metadata.get("task_type", "patch"),
        task_dir=task_dir,
        metadata=metadata,
    )


def load_suite(root: str | Path, suite_name: str) -> list[Task]:
    suite_path = Path(root) / "suites" / f"{suite_name}.json"
    data = load_json(suite_path)
    return [load_task(root, task_id) for task_id in data["task_ids"]]


def discover_tasks(root: str | Path) -> list[Task]:
    tasks: list[Task] = []
    for task_json in sorted((Path(root) / "tasks").glob("*/task.json")):
        tasks.append(load_task(root, task_json.parent.name))
    return tasks
