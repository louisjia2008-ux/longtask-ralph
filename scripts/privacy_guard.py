#!/usr/bin/env python3
"""Fail closed on common private files and credential patterns; never print values.

This is an additional release check, not proof that arbitrary data is anonymous.
Use Gitleaks and review the complete public source and release allowlist too.
"""
from __future__ import annotations

import argparse
import io
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = {
    "private-key": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    "github-token": re.compile(rb"(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})"),
    "provider-token": re.compile(rb"\bsk-(?:proj-|ant-)?[A-Za-z0-9_-]{24,}"),
    "aws-access-key": re.compile(rb"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "telegram-token": re.compile(rb"\b[0-9]{8,12}:[A-Za-z0-9_-]{30,}\b"),
    "credential-url": re.compile(rb"https?://[^\s/<>\"']+:[^\s/<>\"']+@"),
    "personal-absolute-path": re.compile(rb"/(?:Users|Volumes)/[^\s\"'<>]+"),
}
PRIVATE_DIRS = {".ralph", ".obsidian-local-kb", ".local-storage", ".aws", ".ssh"}
PRIVATE_NAMES = {"config.json", "store.json", "pdf-tasks.json", "cookies.json", "auth.json", "data.json", "OBSIDIAN_RUNTIME_TEST_REPORT.md"}
PRIVATE_SUFFIXES = {".sqlite", ".sqlite3", ".db", ".p12", ".pfx", ".pem", ".key"}


def git(*args: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(ROOT), *args], stderr=subprocess.DEVNULL)


def forbidden_path(name: str) -> bool:
    p = PurePosixPath(name)
    return (any(x in PRIVATE_DIRS for x in p.parts)
            or p.name in PRIVATE_NAMES or p.suffix.lower() in PRIVATE_SUFFIXES
            or (p.name.startswith(".env") and p.name not in {".env.example", ".env.sample"}))


def inspect(name: str, data: bytes, findings: list[tuple[str, str]], check_path: bool = True) -> None:
    if check_path and forbidden_path(name):
        findings.append((name, "private-file"))
    for label, pattern in PATTERNS.items():
        if pattern.search(data):
            findings.append((name, label))


def scan_archive(name: str, data: bytes, findings: list[tuple[str, str]]) -> None:
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        for item in archive.infolist():
            if item.is_dir():
                continue
            p = PurePosixPath(item.filename)
            if p.is_absolute() or ".." in p.parts or (item.external_attr >> 16) & 0o170000 == 0o120000:
                findings.append((name, "unsafe-zip-entry"))
                continue
            inspect(f"{name}!{item.filename}", archive.read(item), findings)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--staged", action="store_true", help="Scan complete Git index bytes, not working tree bytes")
    parser.add_argument("--history", action="store_true", help="Scan every object reachable from every local ref")
    parser.add_argument("--artifacts", nargs="+", type=Path, help="Scan explicit raw release files and ZIP contents")
    args = parser.parse_args()
    findings: list[tuple[str, str]] = []
    count = 0
    try:
        if args.artifacts:
            for artifact in args.artifacts:
                data = artifact.read_bytes()
                if artifact.suffix.lower() == ".zip":
                    scan_archive(artifact.name, data, findings)
                else:
                    inspect(artifact.name, data, findings)
                count += 1
        elif args.history:
            for row in git("rev-list", "--objects", "--all").splitlines():
                oid, _, path = row.partition(b" ")
                kind = git("cat-file", "-t", oid.decode()).strip()
                if kind not in {b"blob", b"commit", b"tag"}:
                    continue
                name = path.decode("utf-8", "replace") or kind.decode() + ":" + oid.decode()[:12]
                inspect(name, git("cat-file", kind.decode(), oid.decode()), findings, kind == b"blob")
                count += 1
        else:
            names = git("ls-files", "-z", "--cached").split(b"\0") if args.staged else git("ls-files", "-z", "--cached", "--others", "--exclude-standard").split(b"\0")
            for raw_name in sorted(set(names) - {b""}):
                name = raw_name.decode("utf-8", "strict")
                if args.staged:
                    data = git("show", ":" + name)
                else:
                    file = ROOT / name
                    if file.is_symlink():
                        findings.append((name, "source-symlink-review-required"))
                        continue
                    data = file.read_bytes()
                inspect(name, data, findings)
                count += 1
    except (OSError, ValueError, UnicodeError, subprocess.CalledProcessError, zipfile.BadZipFile) as exc:
        print("Privacy check could not complete (" + type(exc).__name__ + ").", file=sys.stderr)
        return 2
    if findings:
        for name, rule in sorted(set(findings)):
            print(f"BLOCKED: {name}: {rule}", file=sys.stderr)
        return 1
    print(f"Privacy check passed: {count} inputs; review and Gitleaks are separate required gates.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
