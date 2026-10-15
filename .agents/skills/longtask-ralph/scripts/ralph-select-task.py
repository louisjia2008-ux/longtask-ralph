#!/usr/bin/env python3
"""Select the next Ralph atomic task from .ralph/tasks.json."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path.cwd()
TASKS_PATH = ROOT / ".ralph" / "tasks.json"

STATUS_ORDER = {
    "pending": 0,
    "failed_retryable": 1,
}

PRIORITY_ORDER = {
    "high": 0,
    "medium": 1,
    "low": 2,
}


def emit(data: dict[str, Any]) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def main() -> int:
    if not TASKS_PATH.exists():
        emit({"selected": False, "reason": ".ralph/tasks.json does not exist"})
        return 0

    try:
        doc = json.loads(TASKS_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        emit({"selected": False, "reason": f".ralph/tasks.json is invalid JSON: {exc}"})
        return 0

    tasks = doc.get("tasks", [])
    if not isinstance(tasks, list):
        emit({"selected": False, "reason": ".ralph/tasks.json has no tasks array"})
        return 0

    by_id = {task.get("id"): task for task in tasks if isinstance(task, dict)}

    def dependency_done(dep_id: str) -> bool:
        dep = by_id.get(dep_id)
        return bool(dep and dep.get("status") == "done")

    candidates: list[tuple[tuple[int, int, str], dict[str, Any]]] = []
    skipped_reasons: list[str] = []
    for task in tasks:
        if not isinstance(task, dict):
            continue
        task_id = str(task.get("id", ""))
        status = task.get("status")
        if status not in STATUS_ORDER:
            continue
        if task.get("blocked") is True:
            skipped_reasons.append(f"{task_id}: task has blocked=true")
            continue
        attempts = int(task.get("attempts", 0) or 0)
        if attempts >= 3:
            skipped_reasons.append(f"{task_id}: attempts >= 3")
            continue
        dependencies = task.get("dependencies", [])
        if not isinstance(dependencies, list):
            skipped_reasons.append(f"{task_id}: dependencies is not a list")
            continue
        missing = [dep for dep in dependencies if not dependency_done(str(dep))]
        if missing:
            skipped_reasons.append(f"{task_id}: waiting on dependencies {missing}")
            continue
        priority = str(task.get("priority", "medium"))
        sort_key = (
            PRIORITY_ORDER.get(priority, 99),
            STATUS_ORDER[str(status)],
            task_id,
        )
        candidates.append((sort_key, task))

    if not candidates:
        reason = "No pending or retryable task with satisfied dependencies"
        if skipped_reasons:
            reason += "; " + "; ".join(skipped_reasons[:8])
        emit({"selected": False, "reason": reason})
        return 0

    candidates.sort(key=lambda item: item[0])
    emit({"selected": True, "task": candidates[0][1]})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
