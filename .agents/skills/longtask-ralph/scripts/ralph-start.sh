#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
if [ "${1:-}" = "--help" ] || [ "${1:-}" = "-h" ]; then
  echo "Usage: ralph-start.sh [goal]; omit goal to resume. Git automation defaults to off."
  exit 0
fi
REPO_ROOT="${RALPH_REPO_ROOT:-$(pwd -P)}"
cd "$REPO_ROOT"
if [ -e .ralph ] || [ -L .ralph ]; then
  if [ "$#" -gt 0 ]; then
    echo "Existing run preserved. Resume without a goal; review/archive it yourself before a new goal." >&2
    exit 1
  fi
else
  if [ "$#" -eq 0 ]; then echo "A goal is needed for a new run." >&2; exit 1; fi
  bash "$SCRIPT_DIR/ralph-init.sh" "$@"
fi
exec bash "$SCRIPT_DIR/ralph-run.sh"
