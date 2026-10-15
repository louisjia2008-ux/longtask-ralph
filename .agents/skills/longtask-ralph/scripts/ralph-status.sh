#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${RALPH_REPO_ROOT:-$(pwd)}"
REPO_ROOT="$(cd "$REPO_ROOT" && pwd)"
RALPH_DIR="$REPO_ROOT/.ralph"
cd "$REPO_ROOT"

if [ ! -d "$RALPH_DIR" ]; then
  echo "No .ralph/ directory found."
  echo "Initialize first:"
  echo "  \"$SCRIPT_DIR/ralph-start.sh\" \"your goal\""
  exit 1
fi

python3 - "$RALPH_DIR" "$SCRIPT_DIR" <<'PY'
import json
import os
import sys
from pathlib import Path

root = Path(sys.argv[1])
script_dir = Path(sys.argv[2])

def read_text(name, default=""):
    path = root / name
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return default

def read_json(name, default):
    path = root / name
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default
    except json.JSONDecodeError as exc:
        return {"_json_error": str(exc)}

goal = read_text("goal.md", "").strip()
state = read_json("state.json", {})
tasks_doc = read_json("tasks.json", {})
heartbeat = read_text("heartbeat.md", "")
current_task = read_text("current_task.md", "").strip()

tasks = tasks_doc.get("tasks", []) if isinstance(tasks_doc, dict) else []
completed = sum(1 for t in tasks if t.get("status") == "done")
pending = sum(1 for t in tasks if t.get("status") in {"pending", "failed_retryable"})
blocked = sum(1 for t in tasks if t.get("status") == "failed_blocked")

goal_summary = ""
for line in goal.splitlines():
    stripped = line.strip()
    if stripped and not stripped.startswith("#") and not stripped.startswith("Created:") and not stripped.startswith("Updated:"):
        goal_summary = stripped
        break
if not goal_summary and isinstance(tasks_doc, dict):
    goal_summary = tasks_doc.get("goal_summary", "")

logs_dir = root / "logs"
latest_logs = []
if logs_dir.exists():
    latest_logs = sorted((p for p in logs_dir.iterdir() if p.is_file()), key=lambda p: p.stat().st_mtime, reverse=True)[:5]

last_verification = state.get("last_verification", {}) if isinstance(state, dict) else {}
print("Ralph status")
print("============")
print(f"Goal summary: {goal_summary or '(not written yet)'}")
print(f"Current status: {state.get('status', '(unknown)') if isinstance(state, dict) else '(invalid state.json)'}")
print(f"Completion: {state.get('completion', '(unknown)') if isinstance(state, dict) else '(invalid state.json)'}")
print(f"Current iteration: {state.get('current_iteration', 0) if isinstance(state, dict) else 0}")
print(f"Current task: {current_task.splitlines()[0] if current_task else '(none)'}")
print(f"Completed tasks: {completed}")
print(f"Pending/retryable tasks: {pending}")
print(f"Blocked tasks: {blocked}")
print("Last verification:")
print(f"  Status: {last_verification.get('status', 'unknown')}")
print(f"  Command: {last_verification.get('command', '')}")
summary = last_verification.get("summary", "")
if summary:
    print("  Summary: " + summary.replace("\n", "\n           ")[:1200])
print("Latest logs:")
if latest_logs:
    for path in latest_logs:
        print(f"  {path}")
else:
    print("  (no logs yet)")
print("Heartbeat tail:")
lines = heartbeat.splitlines()[-20:]
if lines:
    for line in lines:
        print(f"  {line}")
else:
    print("  (heartbeat is empty)")
print("Suggested next command:")
print(f"  {script_dir / 'ralph-start.sh'}")
PY
