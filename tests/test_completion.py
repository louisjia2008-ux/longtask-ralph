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

    def test_supported_completion_request_survives_host_normalization(self):
        fixture = self.fixture
        fixture.prepare_run()
        fixture.fake.write_text('''#!/usr/bin/env python3
import json, os, subprocess
from pathlib import Path
r = Path('.ralph')
t = json.loads((r / 'tasks.json').read_text())
t['tasks'][0]['status'] = 'done'
(r / 'tasks.json').write_text(json.dumps(t))
(r / 'final_report.md').write_text('# Final report\\n\\nThe synthetic task passed the project verification.\\n')
subprocess.run(['python3', os.environ['STATE_HELPER'], 'set-complete'], check=True)
''')
        result = fixture.script("ralph-run.sh", STATE_HELPER=str(SCRIPTS / "ralph-update-state.py"))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(fixture.state()["completion"], "RALPH_DONE")

    def test_consecutive_verifier_failures_stop_after_three_rounds(self):
        fixture = self.fixture
        fixture.prepare_run(verify_success=False)
        fixture.fake.write_text('''#!/usr/bin/env python3
import os
with open(os.environ['FAKE_CALL_LOG'], 'a') as output:
    output.write('fake invocation\\n')
''')
        result = fixture.script("ralph-run.sh", MAX_ITERATIONS="4")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(fixture.call_log.read_text().count("fake invocation"), 3)
        self.assertEqual(fixture.state()["verifier_failures"], 3)

    def test_agent_verification_status_does_not_reset_host_failure_count(self):
        fixture = self.fixture
        fixture.prepare_run(verify_success=False)
        fixture.fake.write_text('''#!/usr/bin/env python3
import os, subprocess
with open(os.environ['FAKE_CALL_LOG'], 'a') as output:
    output.write('fake invocation\\n')
subprocess.run(['python3', os.environ['STATE_HELPER'], 'set-verification', 'PASS', 'component-test', 'Synthetic component passed'], check=True)
''')
        result = fixture.script("ralph-run.sh", MAX_ITERATIONS="4", STATE_HELPER=str(SCRIPTS / "ralph-update-state.py"))
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(fixture.call_log.read_text().count("fake invocation"), 3)

    def test_malformed_required_field_cannot_bypass_human_review(self):
        fixture = self.fixture
        fixture.prepare_run()
        for value in [None, 0, "", [], "false"]:
            with self.subTest(required=value):
                state = {"status": "complete", "completion": "RALPH_DONE", "current_iteration": 0, "blockers": []}
                tasks = {"tasks": [{"id": "T001", "status": "human_review_needed", "required": value}], "blockers": []}
                (fixture.project / ".ralph/state.json").write_text(json.dumps(state))
                (fixture.project / ".ralph/tasks.json").write_text(json.dumps(tasks))
                (fixture.project / ".ralph/final_report.md").write_text("# Final report\n\nSynthetic report with substantive verification evidence.\n")
                result = fixture.script("ralph-run.sh")
                self.assertNotEqual(result.returncode, 0)
                self.assertNotEqual(fixture.state()["completion"], "RALPH_DONE")

    def test_iteration_limit_returns_failure_when_work_is_incomplete(self):
        fixture = self.fixture
        fixture.prepare_run()
        fixture.fake.write_text("#!/usr/bin/env python3\nprint('Synthetic unfinished task')\n")
        result = fixture.script("ralph-run.sh")
        self.assertNotEqual(result.returncode, 0)
        self.assertNotEqual(fixture.state()["completion"], "RALPH_DONE")

    def test_explicit_optional_pending_task_is_allowed(self):
        fixture = self.fixture
        fixture.prepare_run()
        state = {"status": "complete", "completion": "RALPH_DONE", "current_iteration": 0, "blockers": []}
        tasks = {"tasks": [{"id": "T001", "status": "done"}, {"id": "T002", "status": "pending", "required": False}], "blockers": []}
        (fixture.project / ".ralph/state.json").write_text(json.dumps(state))
        (fixture.project / ".ralph/tasks.json").write_text(json.dumps(tasks))
        (fixture.project / ".ralph/final_report.md").write_text("# Final report\n\nThe required synthetic work passed project verification.\n")
        result = fixture.script("ralph-run.sh")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(fixture.state()["completion"], "RALPH_DONE")


if __name__ == "__main__":
    unittest.main()
