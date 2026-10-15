"""Exercise release guards against index/history/ZIP leaks with disposable data."""
import importlib.util
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "privacy_guard.py"


class PrivacyGuardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "scripts").mkdir()
        shutil.copy2(SCRIPT, self.root / "scripts/privacy_guard.py")
        self.git("init", "-q")
        self.git("config", "user.name", "Fixture")
        self.git("config", "user.email", "fixture@example.invalid")

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.root), *args], check=True,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def guard(self, *args):
        return subprocess.run(["python3", str(self.root / "scripts/privacy_guard.py"), *args],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def test_index_bytes_are_checked_even_when_worktree_is_cleaned(self):
        secret = "ghp_" + "X" * 36
        (self.root / "example.txt").write_text(secret)
        self.git("add", "example.txt")
        (self.root / "example.txt").write_text("safe synthetic example")
        result = self.guard("--staged")
        self.assertEqual(result.returncode, 1)
        self.assertNotIn(secret.encode(), result.stdout + result.stderr)
        self.git("add", "example.txt")
        self.assertEqual(self.guard("--staged").returncode, 0)

    def test_history_cannot_be_hidden_by_deleting_file(self):
        (self.root / "example.txt").write_text("sk-" + "Q" * 30)
        self.git("add", "example.txt")
        self.git("commit", "-qm", "synthetic trigger")
        (self.root / "example.txt").unlink()
        self.git("add", "-u")
        self.git("commit", "-qm", "remove trigger")
        self.assertEqual(self.guard("--history").returncode, 1)

    def test_private_runtime_in_zip_is_blocked(self):
        artifact = self.root / "preview.zip"
        with zipfile.ZipFile(artifact, "w") as z:
            z.writestr("preview/.ralph/state.json", "{}")
        self.assertEqual(self.guard("--artifacts", str(artifact)).returncode, 1)
        with zipfile.ZipFile(artifact, "w") as z:
            z.writestr("preview/README.md", "Synthetic preview")
        self.assertEqual(self.guard("--artifacts", str(artifact)).returncode, 0)

    def test_credential_url_and_personal_path_are_blocked(self):
        artifact = self.root / "example.txt"
        for value in ["https://" + "user:password@example.invalid/api", "/" + "Users" + "/fixture/private"]:
            artifact.write_text(value)
            result = self.guard("--artifacts", str(artifact))
            self.assertEqual(result.returncode, 1)
            self.assertNotIn(value.encode(), result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
