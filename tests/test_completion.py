import json
import subprocess
import unittest

from support import ProjectFixture, SCRIPTS


class CompletionTests(unittest.TestCase):
    def setUp(self):
        self.fixture = ProjectFixture()
        self.addCleanup(self.fixture.cleanup)

    def run_scenario(self, scenario, verify_success=True):
        self.fixture.prepare_run(verify_success=verify_success)
        result = self.fixture.script("ralph-run.sh", FAKE_SCENARIO=scenario)
        self.assertTrue(self.fixture.call_log.exists(), result.stdout + result.stderr)
        return self.fixture.state()

    def test_candidate_done_with_successful_verifier_is_accepted(self):
        self.assertEqual(self.run_scenario("done")["completion"], "RALPH_DONE")

    def test_verifier_failure_cannot_finish(self):
        self.assertNotEqual(self.run_scenario("done", verify_success=False)["completion"], "RALPH_DONE")

    def test_pending_required_task_cannot_finish(self):
        self.assertNotEqual(self.run_scenario("pending")["completion"], "RALPH_DONE")

    def test_missing_report_cannot_finish(self):
        self.assertNotEqual(self.run_scenario("missing-report")["completion"], "RALPH_DONE")

    def test_unresolved_blocker_cannot_finish(self):
        self.assertNotEqual(self.run_scenario("blocker")["completion"], "RALPH_DONE")

    def test_human_review_is_not_completed_required_work(self):
        self.assertNotEqual(self.run_scenario("human-review")["completion"], "RALPH_DONE")

    def test_placeholder_report_cannot_finish(self):
        self.assertNotEqual(self.run_scenario("placeholder-report")["completion"], "RALPH_DONE")

    def test_soft_warning_is_not_acceptance(self):
        fixture = self.fixture
        fixture.prepare_run()
        (fixture.project / ".ralph/custom-verify.sh").write_text("#!/usr/bin/env bash\necho SOFT_WARNING\nexit 0\n")
        fixture.script("ralph-run.sh", FAKE_SCENARIO="done")
        self.assertNotEqual(fixture.state()["completion"], "RALPH_DONE")

    def test_existing_done_resume_rechecks_actual_verifier_without_model(self):
        fixture = self.fixture
        fixture.prepare_run(verify_success=False)
        state = fixture.state()
        state.update({"status": "complete", "completion": "RALPH_DONE", "last_verification": {"status": "PASS"}})
        (fixture.project / ".ralph/state.json").write_text(json.dumps(state))
        result = fixture.script("ralph-run.sh")
        self.assertNotEqual(result.returncode, 0)
        self.assertNotEqual(fixture.state()["completion"], "RALPH_DONE")
        self.assertFalse(fixture.call_log.exists())

    def test_state_cli_completion_routes_only_request_a_candidate(self):
        fixture = self.fixture
        fixture.prepare_run()
        for args in [["set-complete"], ["set-status", "complete", "RALPH_DONE"]]:
            with self.subTest(args=args):
                subprocess.run(["python3", str(SCRIPTS / "ralph-update-state.py"), *args], cwd=fixture.project, env=fixture.env, check=True, capture_output=True)
                self.assertEqual(fixture.state()["completion"], "RALPH_CONTINUE")
                self.assertEqual(fixture.state()["requested_completion"], "RALPH_DONE")


if __name__ == "__main__":
    unittest.main()
