"""Temporary project fixtures and a fake CLI, with no real Codex dependency."""

import json
import os
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / ".agents/skills/longtask-ralph"
SCRIPTS = SKILL / "scripts"

FAKE_CLI = '''#!/usr/bin/env python3
import json, os, subprocess, sys
from pathlib import Path
root = Path.cwd()
call_log = os.environ.get("FAKE_CALL_LOG")
if call_log:
    with open(call_log, "a") as out:
        out.write("fake invocation\\n")
ralph = root / ".ralph"
ralph.mkdir(exist_ok=True)
state_file = ralph / "state.json"
state = json.loads(state_file.read_text()) if state_file.exists() else {}
tasks_file = ralph / "tasks.json"
tasks = json.loads(tasks_file.read_text()) if tasks_file.exists() else {}
scenario = os.environ.get("FAKE_SCENARIO", "done")
task_status = "human_review_needed" if scenario == "human-review" else "done"
if scenario == "pending":
    task_status = "pending"
tasks.update({"version": "0.1", "tasks": [{"id": "T001", "title": "Synthetic task", "status": task_status, "priority": "high", "dependencies": [], "attempts": 0}], "blockers": []})
state.update({"version": "0.1", "status": "complete", "completion": "RALPH_DONE", "blockers": []})
if scenario == "blocker":
    state["blockers"] = [{"reason": "Synthetic unresolved blocker"}]
if scenario == "stage-change":
    (root / "model-change.txt").write_text("Synthetic local change\\n")
    subprocess.run(["git", "add", "--", "model-change.txt"], check=True)
if scenario == "business-change":
    (root / "result.txt").write_text("A verified synthetic business change.\\n")
if scenario == "placeholder-report":
    (ralph / "final_report.md").write_text("# Final Report\\n\\nRun is not complete yet.\\n")
elif scenario != "missing-report":
    (ralph / "final_report.md").write_text("# Synthetic final report\\n\\nOffline fixture evidence only.\\n")
tasks_file.write_text(json.dumps(tasks))
state_file.write_text(json.dumps(state))
print("synthetic CLI output")
'''


class ProjectFixture:
    def __init__(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ralph-test-")
        self.base = Path(self.temp.name)
        self.project = self.base / "project with spaces"
        self.project.mkdir()
        self.fake = self.base / "fake-cli.py"
        self.fake.write_text(FAKE_CLI)
        self.fake.chmod(0o755)
        self.call_log = self.base / "fake-calls.log"
        self.env = {
            "PATH": os.environ.get("PATH", ""),
            "PYTHONDONTWRITEBYTECODE": "1",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_SYSTEM": os.devnull,
            "CODEX_BIN": str(self.fake),
            "MAX_ITERATIONS": "1",
            "SLEEP_SECONDS": "0",
            "FAKE_CALL_LOG": str(self.call_log),
        }

    def cleanup(self):
        self.temp.cleanup()

    def git(self, *args):
        return subprocess.run(
            ["git", "-C", str(self.project), *args], env=self.env,
            capture_output=True, check=True,
        ).stdout

    def create_git(self):
        self.git("init", "-b", "main")
        self.git("config", "user.name", "Fixture Maintainer")
        self.git("config", "user.email", "fixture@example.invalid")
        self.git("config", "core.hooksPath", os.devnull)
        self.git("config", "commit.gpgsign", "false")
        (self.project / "README.md").write_text("Synthetic isolated project.\n")
        self.git("add", "--", "README.md")
        self.git("commit", "-m", "Synthetic fixture baseline")

    def prepare_run(self, *, verify_success=True):
        ralph = self.project / ".ralph"
        ralph.mkdir()
        (ralph / "task_brief.md").write_bytes((SKILL / "templates/task_brief.md").read_bytes())
        (ralph / "goal.md").write_text("Synthetic offline test\n")
        (ralph / "acceptance.md").write_text("Synthetic task is complete.\n")
        (ralph / "plan.md").write_text("One synthetic task.\n")
        (ralph / "progress.md").write_text("# Progress\n")
        (ralph / "heartbeat.md").write_text("# Heartbeat\n")
        (ralph / "tasks.json").write_text(json.dumps({"version": "0.1", "tasks": [{"id": "T001", "status": "pending", "priority": "high", "dependencies": [], "attempts": 0}], "blockers": []}))
        (ralph / "state.json").write_text(json.dumps({"version": "0.1", "status": "running", "completion": "RALPH_CONTINUE", "current_iteration": 0, "blockers": []}))
        verify = ralph / "custom-verify.sh"
        verify.write_text("#!/usr/bin/env bash\nprintf 'Synthetic verifier\\n'\nexit " + ("0" if verify_success else "1") + "\n")
        verify.chmod(0o755)

    def script(self, name, *args, **environment):
        env = self.env.copy()
        env.update(environment)
        return subprocess.run(
            ["bash", str(SCRIPTS / name), *args], cwd=self.project,
            env=env, capture_output=True, text=True, timeout=20,
        )

    def state(self):
        return json.loads((self.project / ".ralph/state.json").read_text())

    def snapshot(self, folder):
        return {str(p.relative_to(folder)): p.read_bytes() for p in folder.rglob("*") if p.is_file()}
