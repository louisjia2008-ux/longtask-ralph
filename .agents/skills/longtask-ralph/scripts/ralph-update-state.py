#!/usr/bin/env python3
"""Small state mutation CLI for Ralph.

This script intentionally uses only Python's standard library.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path.cwd()
RALPH = ROOT / ".ralph"
STATE_PATH = RALPH / "state.json"
TASKS_PATH = RALPH / "tasks.json"


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return default.copy()
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    tmp.replace(path)


def default_state() -> dict[str, Any]:
    stamp = now()
    return {
        "version": "0.1",
        "status": "init",
        "completion": "RALPH_CONTINUE",
        "current_iteration": 0,
        "current_task_id": None,
        "last_task_id": None,
        "last_verification": {"status": "unknown", "command": "", "summary": ""},
        "blockers": [],
        "no_diff_iterations": 0,
        "verifier_failures": 0,
        "started_at": stamp,
        "updated_at": stamp,
    }


def default_tasks() -> dict[str, Any]:
    stamp = now()
    return {
        "version": "0.1",
        "project": "auto-detected",
        "goal_summary": "",
        "acceptance_criteria": [],
        "max_iterations": 100,
        "current_iteration": 0,
        "status": "planning",
        "tasks": [],
        "blockers": [],
        "last_successful_task": None,
        "last_failed_task": None,
        "no_diff_iterations": 0,
        "created_at": stamp,
        "updated_at": stamp,
    }


def load_pair() -> tuple[dict[str, Any], dict[str, Any]]:
    return normalize_state(load_json(STATE_PATH, default_state())), load_json(TASKS_PATH, default_tasks())


def save_pair(state: dict[str, Any], tasks_doc: dict[str, Any]) -> None:
    stamp = now()
    state["updated_at"] = stamp
    tasks_doc["updated_at"] = stamp
    save_json(STATE_PATH, state)
    save_json(TASKS_PATH, tasks_doc)


def normalize_state(raw: dict[str, Any]) -> dict[str, Any]:
    base = default_state()
    if isinstance(raw, dict):
        base["status"] = raw.get("status", base["status"])
        completion = raw.get("completion", base["completion"])
        if completion == "RALPH_COMPLETE":
            completion = "RALPH_DONE"
        base["completion"] = completion
        base["current_iteration"] = raw.get("current_iteration", base["current_iteration"])
        base["current_task_id"] = raw.get("current_task_id", base["current_task_id"])
        base["last_task_id"] = raw.get("last_task_id", base["last_task_id"])
        if isinstance(raw.get("last_verification"), dict):
            base["last_verification"] = raw["last_verification"]
        base["blockers"] = raw.get("blockers", base["blockers"]) if isinstance(raw.get("blockers", []), list) else []
        base["no_diff_iterations"] = raw.get("no_diff_iterations", base["no_diff_iterations"])
        failures = raw.get("verifier_failures", 0)
        base["verifier_failures"] = failures if type(failures) is int and failures >= 0 else 0
        if raw.get("requested_completion") == "RALPH_DONE":
            base["requested_completion"] = "RALPH_DONE"
        base["started_at"] = raw.get("started_at") or raw.get("created_at") or base["started_at"]
        base["updated_at"] = raw.get("updated_at") or base["updated_at"]
        if "completion" not in raw:
            base["completion"] = "RALPH_CONTINUE" if base["status"] != "blocked" else "RALPH_BLOCKED"
    return base


def ensure_state() -> None:
    raw_state = load_json(STATE_PATH, default_state())
    tasks_doc = load_json(TASKS_PATH, default_tasks())
    state = normalize_state(raw_state)
    save_pair(state, tasks_doc)


def find_task(tasks_doc: dict[str, Any], task_id: str) -> dict[str, Any] | None:
    for task in tasks_doc.get("tasks", []):
        if isinstance(task, dict) and task.get("id") == task_id:
            return task
    return None


def add_blocker(target: dict[str, Any], reason: str) -> None:
    blockers = target.setdefault("blockers", [])
    if isinstance(blockers, list):
        blockers.append({"at": now(), "reason": reason})


def append_heartbeat(message: str) -> None:
    path = RALPH / "heartbeat.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(f"\n- {now()}: {message}\n")


def append_progress(message: str) -> None:
    path = RALPH / "progress.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(f"\n## {now()}\n\n{message}\n")


def mark_task_done(task_id: str) -> None:
    state, tasks_doc = load_pair()
    task = find_task(tasks_doc, task_id)
    if not task:
        raise SystemExit(f"Task not found: {task_id}")
    task["status"] = "done"
    task["last_error"] = ""
    tasks_doc["last_successful_task"] = task_id
    state["last_task_id"] = task_id
    state["current_task_id"] = None
    state["status"] = "running"
    state["completion"] = "RALPH_CONTINUE"
    save_pair(state, tasks_doc)


def mark_task_failed(task_id: str, reason: str) -> None:
    state, tasks_doc = load_pair()
    task = find_task(tasks_doc, task_id)
    if not task:
        raise SystemExit(f"Task not found: {task_id}")
    attempts = int(task.get("attempts", 0) or 0) + 1
    task["attempts"] = attempts
    task["last_error"] = reason
    tasks_doc["last_failed_task"] = task_id
    state["last_task_id"] = task_id
    state["current_task_id"] = None
    state["last_verification"] = {
        "status": "FAIL",
        "command": "",
        "summary": reason,
    }
    if attempts >= 3:
        task["status"] = "failed_blocked"
        state["status"] = "blocked"
        state["completion"] = "RALPH_BLOCKED"
        add_blocker(state, f"{task_id} failed {attempts} times: {reason}")
        add_blocker(tasks_doc, f"{task_id} failed {attempts} times: {reason}")
        append_progress(f"BLOCKER: `{task_id}` failed {attempts} times.\n\nReason: {reason}\n\nStatus: RALPH_BLOCKED.")
        append_heartbeat(f"{task_id} blocked after {attempts} failed attempts. Status: RALPH_BLOCKED.")
    else:
        task["status"] = "failed_retryable"
        state["status"] = "running"
        state["completion"] = "RALPH_CONTINUE"
    save_pair(state, tasks_doc)


def mark_blocked(reason: str) -> None:
    state, tasks_doc = load_pair()
    state["status"] = "blocked"
    state["completion"] = "RALPH_BLOCKED"
    add_blocker(state, reason)
    add_blocker(tasks_doc, reason)
    append_progress(f"BLOCKER: {reason}\n\nStatus: RALPH_BLOCKED.")
    append_heartbeat(f"Blocked: {reason}. Status: RALPH_BLOCKED.")
    save_pair(state, tasks_doc)


def increment_iteration() -> None:
    state, tasks_doc = load_pair()
    state["current_iteration"] = int(state.get("current_iteration", 0) or 0) + 1
    tasks_doc["current_iteration"] = int(tasks_doc.get("current_iteration", 0) or 0) + 1
    state["status"] = "running"
    save_pair(state, tasks_doc)


def set_complete() -> None:
    state, tasks_doc = load_pair()
    state["status"] = "running"
    state["completion"] = "RALPH_CONTINUE"
    state["requested_completion"] = "RALPH_DONE"
    append_heartbeat("Completion requested; host verification is still required.")
    save_pair(state, tasks_doc)


def set_continue() -> None:
    state, tasks_doc = load_pair()
    state["completion"] = "RALPH_CONTINUE"
    state.pop("requested_completion", None)
    if state.get("status") in {"init", "planning", "blocked"}:
        state["status"] = "running"
    save_pair(state, tasks_doc)


def set_verification(status: str, command: str, summary: str) -> None:
    state, tasks_doc = load_pair()
    state["last_verification"] = {
        "status": status,
        "command": command,
        "summary": summary,
    }
    if status.upper() == "FAIL":
        state["verifier_failures"] = int(state.get("verifier_failures", 0) or 0) + 1
    else:
        state["verifier_failures"] = 0
    save_pair(state, tasks_doc)


def note_diff() -> None:
    state, tasks_doc = load_pair()
    state["no_diff_iterations"] = 0
    tasks_doc["no_diff_iterations"] = 0
    save_pair(state, tasks_doc)


def note_no_diff() -> None:
    state, tasks_doc = load_pair()
    count = int(state.get("no_diff_iterations", 0) or 0) + 1
    state["no_diff_iterations"] = count
    tasks_doc["no_diff_iterations"] = count
    save_pair(state, tasks_doc)


def set_status(status: str, completion: str | None = None) -> None:
    state, tasks_doc = load_pair()
    if status == "complete" or completion in {"RALPH_COMPLETE", "RALPH_DONE"}:
        state["status"] = "running"
        state["completion"] = "RALPH_CONTINUE"
        state["requested_completion"] = "RALPH_DONE"
    else:
        state["status"] = status
        if completion:
            state["completion"] = completion
            state.pop("requested_completion", None)
    save_pair(state, tasks_doc)


def stop_with_status(status: str, reason: str) -> None:
    state, tasks_doc = load_pair()
    state["status"] = status
    state["completion"] = "RALPH_BLOCKED"
    add_blocker(state, reason)
    add_blocker(tasks_doc, reason)
    append_progress(f"BLOCKER: {reason}\n\nState changed to `{status}`. Status: RALPH_BLOCKED.")
    append_heartbeat(f"Stopped: {reason}. Status: RALPH_BLOCKED.")
    save_pair(state, tasks_doc)


def usage() -> None:
    print(
        """Usage:
  ralph-update-state.py mark-task-done TASK_ID
  ralph-update-state.py mark-task-failed TASK_ID "reason"
  ralph-update-state.py mark-blocked "reason"
  ralph-update-state.py increment-iteration
  ralph-update-state.py ensure-state
  ralph-update-state.py set-complete
  ralph-update-state.py set-done
  ralph-update-state.py set-continue
  ralph-update-state.py set-stopped-max-iterations "reason"
  ralph-update-state.py set-verification STATUS COMMAND SUMMARY
  ralph-update-state.py note-diff
  ralph-update-state.py note-no-diff
  ralph-update-state.py set-status STATUS [COMPLETION]
  ralph-update-state.py stop-max-iterations "reason"
  ralph-update-state.py stop-verifier-failure "reason"
"""
    )


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        usage()
        return 1

    command = argv[1]
    if command == "mark-task-done" and len(argv) == 3:
        mark_task_done(argv[2])
    elif command == "mark-task-failed" and len(argv) >= 4:
        mark_task_failed(argv[2], " ".join(argv[3:]))
    elif command == "mark-blocked" and len(argv) >= 3:
        mark_blocked(" ".join(argv[2:]))
    elif command == "increment-iteration":
        increment_iteration()
    elif command == "ensure-state":
        ensure_state()
    elif command in {"set-complete", "set-done"}:
        set_complete()
    elif command == "set-continue":
        set_continue()
    elif command == "set-stopped-max-iterations" and len(argv) >= 3:
        stop_with_status("stopped_max_iterations", " ".join(argv[2:]))
    elif command == "set-verification" and len(argv) >= 5:
        set_verification(argv[2], argv[3], " ".join(argv[4:]))
    elif command == "note-diff":
        note_diff()
    elif command == "note-no-diff":
        note_no_diff()
    elif command == "set-status" and len(argv) >= 3:
        set_status(argv[2], argv[3] if len(argv) >= 4 else None)
    elif command == "stop-max-iterations" and len(argv) >= 3:
        stop_with_status("stopped_max_iterations", " ".join(argv[2:]))
    elif command == "stop-verifier-failure" and len(argv) >= 3:
        stop_with_status("stopped_verifier_failure", " ".join(argv[2:]))
    else:
        usage()
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
