"""Offline syntax and installable artifact checks; no model process is used."""

import ast
import hashlib
import importlib.util
import os
import stat
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / ".agents/skills/longtask-ralph"


class LayoutTests(unittest.TestCase):
    def test_shell_syntax(self):
        for script in sorted((SKILL / "scripts").glob("*.sh")):
            with self.subTest(script=script.name):
                result = subprocess.run(["bash", "-n", str(script)], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_python_syntax(self):
        for folder in [SKILL / "scripts", ROOT / "scripts"]:
            for script in sorted(folder.glob("*.py")):
                with self.subTest(script=script.name):
                    ast.parse(script.read_text())
                    compile(script.read_text(), str(script), "exec")

    def test_release_is_one_allowlisted_root_with_license(self):
        spec = importlib.util.spec_from_file_location("release_builder", ROOT / "scripts/build-release.py")
        builder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(builder)
        with tempfile.TemporaryDirectory(prefix="ralph-package-") as temp:
            archive = builder.build(Path(temp))
            with zipfile.ZipFile(archive) as package:
                names = package.namelist()
                expected = {"longtask-ralph/" + name for name in builder.SKILL_FILES}
                expected.update({"longtask-ralph/LICENSE", "longtask-ralph/INSTALL.md"})
                self.assertEqual(set(names), expected)
                self.assertEqual(len(names), len(expected))
                self.assertIn(b"louisjia2008-ux", package.read("longtask-ralph/LICENSE"))
                self.assertTrue(all(name.split("/")[0] == "longtask-ralph" for name in names))
                script = package.getinfo("longtask-ralph/scripts/ralph-start.sh")
                self.assertTrue((script.external_attr >> 16) & stat.S_IXUSR)
                package.extractall(Path(temp) / "installed")
            installed = Path(temp) / "installed/longtask-ralph"
            self.assertTrue((installed / "SKILL.md").is_file())
            for source in builder.SKILL_FILES:
                self.assertEqual((SKILL / source).read_bytes(), (installed / source).read_bytes())
            digest = hashlib.sha256(archive.read_bytes()).hexdigest()
            self.assertEqual(archive.with_suffix(".zip.sha256").read_text().split()[0], digest)

    def test_release_reproducible(self):
        spec = importlib.util.spec_from_file_location("release_builder_repeat", ROOT / "scripts/build-release.py")
        builder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(builder)
        with tempfile.TemporaryDirectory(prefix="ralph-repeat-") as temp:
            first = builder.build(Path(temp) / "first").read_bytes()
            second = builder.build(Path(temp) / "second").read_bytes()
            self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
