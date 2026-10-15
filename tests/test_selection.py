import json
import subprocess
import unittest

from support import ProjectFixture, SCRIPTS


class SelectionTests(unittest.TestCase):
    def setUp(self):
        self.fixture = ProjectFixture()
        self.addCleanup(self.fixture.cleanup)
        self.fixture.prepare_run()

    def select(self, tasks):
        (self.fixture.project / ".ralph/tasks.json").write_text(json.dumps({"tasks": tasks}))
        result = subprocess.run(["python3", str(SCRIPTS / "ralph-select-task.py")], cwd=self.fixture.project, env=self.fixture.env, check=True, capture_output=True, text=True)
        return json.loads(result.stdout)

    def task(self, identifier, status="pending", priority="medium", **extra):
        return {"id": identifier, "status": status, "priority": priority, "dependencies": [], "attempts": 0, **extra}

    def test_priority_before_retry_status(self):
        selected = self.select([self.task("low", priority="low"), self.task("high-retry", status="failed_retryable", priority="high")])
        self.assertEqual(selected["task"]["id"], "high-retry")

    def test_pending_before_retry_at_equal_priority(self):
        selected = self.select([self.task("retry", status="failed_retryable"), self.task("pending")])
        self.assertEqual(selected["task"]["id"], "pending")

    def test_dependency_block_and_attempt_limits(self):
        selected = self.select([self.task("dependency", status="pending"), self.task("waiting", priority="high", dependencies=["dependency"]), self.task("blocked", priority="high", blocked=True), self.task("exhausted", priority="high", attempts=3)])
        self.assertEqual(selected["task"]["id"], "dependency")

    def test_no_eligible_task(self):
        self.assertFalse(self.select([self.task("finished", status="done")])["selected"])

    def test_host_records_the_selected_task(self):
        self.select([self.task("low", priority="low"), self.task("high", priority="high")])
        result = subprocess.run(["python3", str(SCRIPTS / "ralph-host.py"), "select-task"], cwd=self.fixture.project, env=self.fixture.env, check=True, capture_output=True)
        self.assertEqual(result.stdout.strip(), b"selected")
        self.assertEqual(self.fixture.state()["current_task_id"], "high")
        self.assertIn('"id": "high"', (self.fixture.project / ".ralph/current_task.md").read_text())


if __name__ == "__main__":
    unittest.main()
