#!/usr/bin/env python3
"""Compact Ralph progress and summarize large logs without deleting originals."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path.cwd()
RALPH = ROOT / ".ralph"
LOGS = RALPH / "logs"
ARTIFACTS = RALPH / "artifacts"
PROGRESS = RALPH / "progress.md"
LOG_COMPACTION = ARTIFACTS / "log_compaction.md"
PROGRESS_COMPACTION = ARTIFACTS / "progress_archive.md"

MAX_PROGRESS_BYTES = 200 * 1024
KEEP_PROGRESS_BYTES = 80 * 1024
LARGE_LOG_BYTES = 128 * 1024
DELETE_OLD_LOGS = os.environ.get("RALPH_DELETE_OLD_LOGS") == "1"


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def summarize_jsonl(path: Path) -> str:
    lines = []
    total = 0
    statuses = []
    text_fragments = []
    try:
        with path.open("r", encoding="utf-8", errors="replace") as f:
            for raw in f:
                total += 1
                if len(text_fragments) >= 8 and len(statuses) >= 4:
                    continue
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    item = json.loads(raw)
                except json.JSONDecodeError:
                    if len(text_fragments) < 8:
                        text_fragments.append(raw[:240])
                    continue
                if isinstance(item, dict):
                    for key in ("type", "status", "event"):
                        if key in item and len(statuses) < 4:
                            statuses.append(f"{key}={item[key]}")
                    for key in ("message", "text", "content", "summary"):
                        value = item.get(key)
                        if isinstance(value, str) and value.strip() and len(text_fragments) < 8:
                            text_fragments.append(value.strip()[:240])
                            break
    except FileNotFoundError:
        return ""

    lines.append(f"### {path.name}")
    lines.append("")
    lines.append(f"- Size: {path.stat().st_size} bytes")
    lines.append(f"- Lines: {total}")
    if statuses:
        lines.append(f"- Events: {', '.join(statuses)}")
    if text_fragments:
        lines.append("- Sample:")
        for item in text_fragments:
            lines.append(f"  - {item}")
    else:
        lines.append("- Sample: no textual content extracted")
    lines.append("")
    return "\n".join(lines)


def compact_logs() -> None:
    if not LOGS.exists():
        return
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    entries = []
    jsonl_logs = sorted(LOGS.glob("*.jsonl"), key=lambda p: p.stat().st_mtime)
    recent = set(jsonl_logs[-10:])
    for path in jsonl_logs:
        if path.stat().st_size < LARGE_LOG_BYTES and path in recent:
            continue
        summary = summarize_jsonl(path)
        if summary:
            entries.append(summary)
        if DELETE_OLD_LOGS and path not in recent:
            path.unlink()

    if entries:
        LOG_COMPACTION.write_text(
            "# Ralph Log Compaction\n\n"
            f"Updated: {now()}\n\n"
            + "\n".join(entries),
            encoding="utf-8",
        )


def compact_progress() -> None:
    if not PROGRESS.exists() or PROGRESS.stat().st_size <= MAX_PROGRESS_BYTES:
        return
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    data = PROGRESS.read_bytes()
    old = data[:-KEEP_PROGRESS_BYTES]
    recent = data[-KEEP_PROGRESS_BYTES:]
    old_text = old.decode("utf-8", errors="replace")
    recent_text = recent.decode("utf-8", errors="replace")

    summary_lines = [
        "# Ralph Progress Compaction",
        "",
        f"Updated: {now()}",
        "",
        f"Compacted {len(old)} bytes from `.ralph/progress.md`.",
        "",
        "## Oldest Headings",
        "",
    ]
    headings = [line for line in old_text.splitlines() if line.startswith("#")][:80]
    if headings:
        summary_lines.extend(f"- {line.lstrip('#').strip()}" for line in headings)
    else:
        summary_lines.append("- No markdown headings found in compacted section.")
    summary_lines.append("")
    PROGRESS_COMPACTION.write_text("\n".join(summary_lines), encoding="utf-8")

    PROGRESS.write_text(
        "# Ralph Progress\n\n"
        f"Older progress was compacted at {now()} into `.ralph/artifacts/progress_archive.md`.\n\n"
        "## Recent Progress\n\n"
        + recent_text,
        encoding="utf-8",
    )


def main() -> int:
    if not RALPH.exists():
        return 0
    compact_logs()
    compact_progress()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
