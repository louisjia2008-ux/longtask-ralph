import os
import unittest
from pathlib import Path

from support import ProjectFixture


class GitSafetyTests(unittest.TestCase):
    def setUp(self):
        self.fixture = ProjectFixture()
        self.addCleanup(self.fixture.cleanup)

    def test_default_init_does_not_create_git(self):
        fixture = self.fixture
        result = fixture.script("ralph-init.sh", "Synthetic goal")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse((fixture.project / ".git").exists())
        self.assertFalse((fixture.project / ".gitignore").exists())

    def test_default_init_preserves_config_index_and_ignore(self):
        fixture = self.fixture
        fixture.create_git()
        (fixture.project / ".gitignore").write_text("fixture-private/\n")
        (fixture.project / "user-staged.txt").write_text("User-owned staged content.\n")
        fixture.git("add", "--", "user-staged.txt")
        before = {name: (fixture.project / name).read_bytes() for name in [".git/config", ".git/index", ".gitignore"]}
        result = fixture.script("ralph-init.sh", "Synthetic goal")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        for name, data in before.items():
            self.assertEqual((fixture.project / name).read_bytes(), data, name)

    def test_optin_refuses_dirty_start_without_consuming_index(self):
        fixture = self.fixture
        fixture.create_git()
        (fixture.project / "user-staged.txt").write_text("User-owned staged content.\n")
        fixture.git("add", "--", "user-staged.txt")
        before = (fixture.project / ".git/index").read_bytes()
        result = fixture.script("ralph-init.sh", "Synthetic goal", AUTO_COMMIT="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((fixture.project / ".git/index").read_bytes(), before)
        self.assertFalse(fixture.call_log.exists())

    def test_optin_refuses_untracked_start(self):
        fixture = self.fixture
        fixture.create_git()
        (fixture.project / "user-untracked.txt").write_text("Unreviewed local file.\n")
        before = fixture.git("rev-parse", "HEAD")
        result = fixture.script("ralph-init.sh", "Synthetic goal", AUTO_COMMIT="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(fixture.git("rev-parse", "HEAD"), before)
        self.assertFalse(fixture.call_log.exists())

    def test_ancestor_git_is_never_used(self):
        fixture = self.fixture
        fixture.create_git()
        child = fixture.project / "nested"
        child.mkdir()
        before = fixture.snapshot(fixture.project / ".git")
        result = fixture.script("ralph-init.sh", "Synthetic goal", RALPH_REPO_ROOT=str(child), AUTO_COMMIT="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(fixture.snapshot(fixture.project / ".git"), before)
        self.assertFalse(fixture.call_log.exists())

    def test_existing_run_init_and_replacement_goal_are_refused(self):
        fixture = self.fixture
        fixture.prepare_run()
        before = fixture.snapshot(fixture.project / ".ralph")
        first = fixture.script("ralph-init.sh", "Replacement goal")
        second = fixture.script("ralph-start.sh", "Replacement goal")
        self.assertNotEqual(first.returncode, 0)
        self.assertNotEqual(second.returncode, 0)
        self.assertEqual(fixture.snapshot(fixture.project / ".ralph"), before)
        self.assertFalse(fixture.call_log.exists())

    def test_optin_refuses_unstaged_start(self):
        fixture = self.fixture
        fixture.create_git()
        (fixture.project / "README.md").write_text("User-owned unstaged change.\n")
        before = fixture.git("rev-parse", "HEAD")
        result = fixture.script("ralph-init.sh", "Synthetic goal", AUTO_COMMIT="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(fixture.git("rev-parse", "HEAD"), before)
        self.assertFalse(fixture.call_log.exists())

    def test_redirect_environment_is_refused_without_writes(self):
        fixture = self.fixture
        fixture.create_git()
        before = fixture.snapshot(fixture.project / ".git")
        result = fixture.script("ralph-init.sh", "Synthetic goal", GIT_INDEX_FILE=str(fixture.base / "redirected-index"))
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((fixture.project / ".ralph").exists())
        self.assertFalse((fixture.base / "redirected-index").exists())
        self.assertEqual(fixture.snapshot(fixture.project / ".git"), before)

    def test_symlink_target_resolves_to_the_actual_root(self):
        fixture = self.fixture
        fixture.create_git()
        alias = fixture.base / "project-alias"
        alias.symlink_to(fixture.project, target_is_directory=True)
        before = (fixture.project / ".git/config").read_bytes()
        result = fixture.script("ralph-init.sh", "Synthetic goal", RALPH_REPO_ROOT=str(alias))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual((fixture.project / ".git/config").read_bytes(), before)

    def test_legal_optin_completion_commits_business_change_and_preserves_identity(self):
        fixture = self.fixture
        fixture.create_git()
        fixture.prepare_run()
        before_config = (fixture.project / ".git/config").read_bytes()
        before_head = fixture.git("rev-parse", "HEAD")
        result = fixture.script("ralph-run.sh", AUTO_COMMIT="1", FAKE_SCENARIO="business-change")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(fixture.state()["completion"], "RALPH_DONE")
        self.assertNotEqual(fixture.git("rev-parse", "HEAD"), before_head)
        self.assertEqual(fixture.git("show", "HEAD:result.txt"), b"A verified synthetic business change.\n")
        self.assertEqual(fixture.git("diff", "--cached", "--name-only"), b"")
        self.assertEqual((fixture.project / ".git/config").read_bytes(), before_config)
        self.assertNotIn(b".ralph/", fixture.git("ls-files"))

    def test_staging_during_iteration_is_not_consumed_by_final_checkpoint(self):
        fixture = self.fixture
        fixture.create_git()
        fixture.prepare_run()
        before_head = fixture.git("rev-parse", "HEAD")
        result = fixture.script("ralph-run.sh", AUTO_COMMIT="1", FAKE_SCENARIO="stage-change")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(fixture.git("rev-parse", "HEAD"), before_head)
        self.assertEqual(fixture.git("diff", "--cached", "--name-only").strip(), b"model-change.txt")
        self.assertNotEqual(fixture.state()["completion"], "RALPH_DONE")

    def test_run_state_symlink_is_refused(self):
        fixture = self.fixture
        outside = fixture.base / "external-state"
        outside.mkdir()
        (outside / "marker.txt").write_text("External state must remain unchanged.\n")
        (fixture.project / ".ralph").symlink_to(outside, target_is_directory=True)
        before = fixture.snapshot(outside)
        result = fixture.script("ralph-run.sh")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(fixture.snapshot(outside), before)


if __name__ == "__main__":
    unittest.main()
