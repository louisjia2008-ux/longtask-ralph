#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="${RALPH_REPO_ROOT:-$(pwd -P)}"
cd "$REPO_ROOT"
failed=0
for tool in git python3 "${CODEX_BIN:-codex}"; do
  if command -v "$tool" >/dev/null 2>&1; then
    printf 'PASS: %s is available\n' "$tool"
  else
    printf 'MISSING: %s\n' "$tool"
    failed=1
  fi
done
if ! python3 "$SCRIPT_DIR/ralph-host.py" root-check; then failed=1; fi
printf 'AUTO_GIT_INIT=%s AUTO_COMMIT=%s (both default to 0)\n' "${AUTO_GIT_INIT:-0}" "${AUTO_COMMIT:-0}"
echo "Doctor is read-only. Git identity, index and ignore files are not changed."
echo "Codex availability is not authentication, provider, quota or task acceptance."
exit "$failed"
