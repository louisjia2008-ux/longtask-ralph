#!/usr/bin/env python3
"""Build an allowlisted installable skill ZIP without invoking Codex or Git."""

from __future__ import annotations

import argparse
import hashlib
import stat
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / ".agents/skills/longtask-ralph"
VERSION = "0.1.0"
SKILL_FILES = (
    "SKILL.md", "agents/openai.yaml",
    "prompts/iteration.md", "prompts/phase0_mission_lock.md",
    "references/phase_workflow.md", "references/project_profiles.md",
    "references/ralph_protocol.md", "references/safety_policy.md",
    "references/task_contract.md", "references/verifier_strategy.md",
    "scripts/ralph-compact.py", "scripts/ralph-doctor.sh",
    "scripts/ralph-init.sh", "scripts/ralph-run.sh",
    "scripts/ralph-host.py",
    "scripts/ralph-select-task.py", "scripts/ralph-start.sh",
    "scripts/ralph-status.sh", "scripts/ralph-update-state.py",
    "scripts/ralph-verify.sh", "templates/acceptance_report.md",
    "templates/progress_log.md", "templates/task_brief.md",
)


def build(output: Path) -> Path:
    inputs = [(SKILL / name, name) for name in SKILL_FILES]
    inputs += [(ROOT / "LICENSE", "LICENSE"), (ROOT / "docs/INSTALL.md", "INSTALL.md")]
    for source, name in inputs:
        if source.is_symlink() or not source.is_file():
            raise ValueError(f"Missing regular release input: {name}")
        source.resolve().relative_to(ROOT)
    output.mkdir(parents=True, exist_ok=True)
    archive = output / f"longtask-ralph-{VERSION}.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as target:
        for source, name in inputs:
            entry = zipfile.ZipInfo("longtask-ralph/" + name, (2026, 1, 1, 0, 0, 0))
            entry.create_system = 3
            entry.compress_type = zipfile.ZIP_DEFLATED
            permissions = 0o755 if source.stat().st_mode & 0o111 else 0o644
            entry.external_attr = (stat.S_IFREG | permissions) << 16
            target.writestr(entry, source.read_bytes())
    checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
    archive.with_suffix(archive.suffix + ".sha256").write_text(
        f"{checksum}  {archive.name}\n", encoding="utf-8"
    )
    (output / "SHA256SUMS").write_text(f"{checksum}  {archive.name}\n", encoding="utf-8")
    return archive


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(build(args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
