#!/usr/bin/env python3
"""Host-side repository and completion checks. No model or network calls."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REDIRECT_ENV = (
    "GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR",
    "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    "GIT_CONFIG", "GIT_CONFIG_COUNT", "GIT_CONFIG_PARAMETERS",
)


def stamp():
    return datetime.now(timezone.utc).isoformat()


def git(root, *args, check=True):
    env = os.environ.copy()
    env["GIT_OPTIONAL_LOCKS"] = "0"
    result = subprocess.run(
        ["git", "--literal-pathspecs", "-c", "core.fsmonitor=false", "-C", str(root), *args],
        env=env, capture_output=True,
    )
    if check and result.returncode:
        raise ValueError("Git operation failed: " + args[0])
    return result


def root_check():
    if any(name in os.environ for name in REDIRECT_ENV):
        raise ValueError("Git redirect environment is not allowed")
    root = Path.cwd().resolve(strict=True)
    result = git(root, "rev-parse", "--show-toplevel", check=False)
    if result.returncode == 0:
        actual = Path(os.fsdecode(result.stdout).strip()).resolve(strict=True)
        if actual != root:
            raise ValueError("Target must be the exact Git root, not a nested project")
        return root, True
    if (root / ".git").exists() or (root / ".git").is_symlink():
        raise ValueError("Existing Git metadata could not be resolved safely")
    return root, False


def runtime_check(root, *, required=False):
    runtime = root / ".ralph"
    if runtime.is_symlink():
        raise ValueError("Run state must not be a symlink")
    if required and not runtime.is_dir():
        raise ValueError("No existing run; initialize a goal first")
    if runtime.exists() and not runtime.is_dir():
        raise ValueError("Run state is not a directory")
    if runtime.is_dir():
        for path in runtime.rglob("*"):
            if path.is_symlink():
                raise ValueError("Run state contains a symlink")
    return runtime


def entries(root, *args):
    return [os.fsdecode(item) for item in git(root, *args).stdout.split(b"\0") if item]


def is_runtime(name):
    return name == ".ralph" or name.startswith(".ralph/")


def staged(root):
    return entries(root, "diff", "--cached", "--name-only", "-z")


def business_changes(root):
    changed = entries(root, "ls-files", "--modified", "--deleted", "-z")
    changed += entries(root, "ls-files", "--others", "--exclude-standard", "-z")
    return sorted({name for name in changed if not is_runtime(name)})


def checkpoint_ready(root, *, clean=False):
    if git(root, "rev-parse", "--verify", "HEAD", check=False).returncode:
        raise ValueError("Create a reviewed initial Git baseline manually before enabling checkpoints")
    for name in ("user.name", "user.email"):
        if not git(root, "config", "--get", name, check=False).stdout.strip():
            raise ValueError("Configure Git identity yourself before enabling checkpoints")
    if staged(root):
        raise ValueError("Existing staged changes are user-owned; checkpoint refused")
    if clean and business_changes(root):
        raise ValueError("Checkpoint start requires clean business files, including untracked files")


def preflight(mode):
    root, has_git = root_check()
    runtime = runtime_check(root, required=mode == "run")
    if mode == "init" and runtime.exists():
        raise ValueError("Existing run preserved; resume without a replacement goal")
    auto_init = os.environ.get("AUTO_GIT_INIT", "0")
    auto_commit = os.environ.get("AUTO_COMMIT", "0")
    if auto_init not in ("0", "1") or auto_commit not in ("0", "1"):
        raise ValueError("Git automation flags must be 0 or 1")
    if not has_git and auto_init == "1":
        git(root, "init")
        has_git = True
    if auto_commit == "1":
        if not has_git:
            raise ValueError("Checkpoints require a reviewed Git root and baseline")
        checkpoint_ready(root, clean=True)
    if mode == "run":
        for filename in ("task_brief.md", "tasks.json", "state.json"):
            path = runtime / filename
            if not path.is_file() or not path.read_text().strip():
                raise ValueError("Required run file missing or empty: " + filename)
        if "## 10. Git Safety" not in (runtime / "task_brief.md").read_text():
            raise ValueError("Phase 0 Git Safety contract is missing")


def checkpoint(message):
    root, has_git = root_check()
    runtime_check(root, required=True)
    if os.environ.get("AUTO_COMMIT", "0") != "1":
        return
    if not has_git:
        raise ValueError("Checkpoint target is not a Git root")
    checkpoint_ready(root)
    paths = business_changes(root)
    if not paths:
        return
    git(root, "add", "--all", "--", *paths)
    if set(staged(root)) != set(paths):
        raise ValueError("Index changed during checkpoint; preserving staged work without committing")
    git(root, "commit", "-m", message)


def load(path):
    with path.open(encoding="utf-8") as stream:
        data = json.load(stream)
    if not isinstance(data, dict):
        raise ValueError("Expected a JSON object in run state")
    return data


def save(path, data):
    temporary = path.with_suffix(path.suffix + ".host-tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def record_verification(status):
    root, _ = root_check()
    runtime = runtime_check(root, required=True)
    state = load(runtime / "state.json")
    record = {"status": status, "iteration": state.get("current_iteration", 0), "checked_at": stamp()}
    save(runtime / "host-verification.json", record)
    state["last_verification"] = record.copy()
    state["verifier_failures"] = int(state.get("verifier_failures", 0)) + 1 if status == "FAIL" else 0
    if status != "PASS" and (state.get("completion") in ("RALPH_DONE", "RALPH_COMPLETE") or state.get("requested_completion") == "RALPH_DONE"):
        state["completion"] = "RALPH_CONTINUE"
        state["requested_completion"] = "RALPH_DONE"
    save(runtime / "state.json", state)


def completion_errors(root, state, tasks):
    runtime = root / ".ralph"
    errors = []
    evidence = runtime / "host-verification.json"
    verification = load(evidence) if evidence.is_file() else {}
    if verification.get("status") != "PASS" or verification.get("iteration") != state.get("current_iteration", 0):
        errors.append("Latest host verifier must be PASS; soft warnings are not acceptance")
    if state.get("last_verification", {}).get("status") != "PASS":
        errors.append("Latest verification is not PASS")
    if state.get("blockers") or tasks.get("blockers") or state.get("status") == "blocked":
        errors.append("Unresolved run blockers")
    queue = tasks.get("tasks")
    if not isinstance(queue, list) or not queue:
        errors.append("A nonempty required-task queue is needed")
    else:
        for task in queue:
            if not isinstance(task, dict):
                errors.append("Invalid task record")
                continue
            if task.get("blocked") or task.get("status") == "failed_blocked":
                errors.append("Blocked task remains")
            if task.get("required", True) and task.get("status") != "done":
                errors.append("Required task is not done")
    report = runtime / "final_report.md"
    if not report.is_file() or report.is_symlink():
        errors.append("A final report is required")
    else:
        text = report.read_text(encoding="utf-8").strip()
        template = Path(__file__).resolve().parents[1] / "templates/acceptance_report.md"
        body = " ".join(line.strip() for line in text.splitlines() if line.strip() and not line.lstrip().startswith("#"))
        placeholders = ("Run is not complete yet.", "Initialization has not completed", "RALPH_CONTINUE / RALPH_DONE / RALPH_BLOCKED")
        if len(body) < 20 or any(marker in text for marker in placeholders) or (template.is_file() and text == template.read_text().strip()):
            errors.append("Final report is empty or still a placeholder")
    return errors


def finish():
    root, _ = root_check()
    runtime = runtime_check(root, required=True)
    state = load(runtime / "state.json")
    tasks = load(runtime / "tasks.json")
    errors = completion_errors(root, state, tasks)
    if errors:
        state["completion"] = "RALPH_BLOCKED"
        state["status"] = "blocked"
        state.setdefault("blockers", []).append({"at": stamp(), "reason": "; ".join(errors)})
    else:
        state["completion"] = "RALPH_DONE"
        state["status"] = "complete"
        tasks["status"] = "complete"
    state.pop("requested_completion", None)
    save(runtime / "state.json", state)
    save(runtime / "tasks.json", tasks)
    if errors:
        raise ValueError("Completion refused: " + "; ".join(errors))


def field(name):
    state = load(Path.cwd() / ".ralph/state.json")
    if name == "completion" and state.get("requested_completion") == "RALPH_DONE":
        print("RALPH_DONE")
    else:
        value = state.get(name, "")
        print("RALPH_DONE" if value == "RALPH_COMPLETE" else value)


def planning_complete():
    root, _ = root_check()
    runtime = runtime_check(root, required=True)
    state = load(runtime / "state.json")
    state["completion"] = "RALPH_CONTINUE"
    state["status"] = "planning"
    state.pop("requested_completion", None)
    save(runtime / "state.json", state)


def select_task():
    root, _ = root_check()
    runtime = runtime_check(root, required=True)
    selector = Path(__file__).with_name("ralph-select-task.py")
    result = subprocess.run([sys.executable, str(selector)], capture_output=True, check=True)
    selection = json.loads(result.stdout)
    if not selection.get("selected"):
        print("none")
        return
    task = selection["task"]
    state = load(runtime / "state.json")
    state["current_task_id"] = task["id"]
    state["status"] = "running"
    save(runtime / "state.json", state)
    (runtime / "current_task.md").write_text(
        "# Current atomic task\n\n" + json.dumps(task, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print("selected")


def main():
    try:
        command = sys.argv[1]
        if command in ("preflight-init", "preflight-run"):
            preflight(command.split("-", 1)[1])
        elif command == "checkpoint":
            checkpoint(sys.argv[2])
        elif command == "record-verification":
            record_verification(sys.argv[2])
        elif command == "finish":
            finish()
        elif command == "field":
            field(sys.argv[2])
        elif command == "planning-complete":
            planning_complete()
        elif command == "root-check":
            root, _ = root_check()
            runtime_check(root)
            print(root)
        elif command == "select-task":
            select_task()
        else:
            raise ValueError("Unknown host action")
        return 0
    except (ValueError, OSError, KeyError, json.JSONDecodeError, IndexError, subprocess.CalledProcessError) as error:
        print("[ralph-host] " + str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
