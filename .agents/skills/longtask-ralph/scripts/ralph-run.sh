#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="${RALPH_REPO_ROOT:-$(pwd -P)}"
cd "$REPO_ROOT"
REPO_ROOT="$(pwd -P)"
MAX_ITERATIONS="${MAX_ITERATIONS:-80}"
MAX_HOURS="${MAX_HOURS:-}"
SLEEP_SECONDS="${SLEEP_SECONDS:-5}"
SANDBOX="${SANDBOX:-workspace-write}"
CODEX_BIN="${CODEX_BIN:-codex}"
MODEL_ARGS="${MODEL_ARGS:-}"
AUTO_GIT_INIT="${AUTO_GIT_INIT:-0}"
AUTO_COMMIT="${AUTO_COMMIT:-0}"
export AUTO_GIT_INIT AUTO_COMMIT
case "$MAX_ITERATIONS" in ''|*[!0-9]*) echo "MAX_ITERATIONS must be a positive integer" >&2; exit 1;; esac
if [ "$MAX_ITERATIONS" -lt 1 ]; then echo "MAX_ITERATIONS must be positive" >&2; exit 1; fi
case "$MAX_HOURS" in *[!0-9]*) echo "MAX_HOURS must be integer hours" >&2; exit 1;; esac
python3 "$SCRIPT_DIR/ralph-host.py" preflight-run
field() { python3 "$SCRIPT_DIR/ralph-host.py" field "$1"; }
verify() {
  local label="$1"
  local result=0
  set +e
  bash "$SCRIPT_DIR/ralph-verify.sh" > ".ralph/logs/$label.verify.log" 2>&1
  result=$?
  set -e
  if [ "$result" -ne 0 ]; then
    python3 "$SCRIPT_DIR/ralph-host.py" record-verification FAIL
  elif grep -q 'SOFT_WARNING' ".ralph/logs/$label.verify.log"; then
    python3 "$SCRIPT_DIR/ralph-host.py" record-verification SOFT_WARNING
  else
    python3 "$SCRIPT_DIR/ralph-host.py" record-verification PASS
  fi
}
mkdir -p .ralph/logs
# An existing DONE is a candidate: rerun the actual verifier before trusting it.
if [ "$(field completion)" = "RALPH_DONE" ]; then
  verify resume
  python3 "$SCRIPT_DIR/ralph-host.py" finish
  if ! python3 "$SCRIPT_DIR/ralph-host.py" checkpoint "ralph: verified completion"; then
    python3 "$SCRIPT_DIR/ralph-update-state.py" mark-blocked "Checkpoint refused; staged work is preserved"
    exit 1
  fi
  exit $?
fi
model_args=()
if [ -n "$MODEL_ARGS" ]; then read -r -a model_args <<< "$MODEL_ARGS"; fi
start_epoch="$(date +%s)"
count=0
while [ "$count" -lt "$MAX_ITERATIONS" ]; do
  if [ -n "$MAX_HOURS" ] && [ "$(( $(date +%s) - start_epoch ))" -ge "$(( MAX_HOURS * 3600 ))" ]; then
    python3 "$SCRIPT_DIR/ralph-update-state.py" mark-blocked "Reached the between-iteration hour limit"
    exit 1
  fi
  count=$((count + 1))
  python3 "$SCRIPT_DIR/ralph-update-state.py" increment-iteration
  label="iteration-$(printf '%04d' "$(field current_iteration)")"
  if ! selection="$(python3 "$SCRIPT_DIR/ralph-host.py" select-task)"; then
    python3 "$SCRIPT_DIR/ralph-update-state.py" mark-blocked "Task selection failed; inspect the preserved queue"
    exit 1
  fi
  if [ "$selection" = "none" ]; then
    verify "$label"
    python3 "$SCRIPT_DIR/ralph-host.py" finish
    if ! python3 "$SCRIPT_DIR/ralph-host.py" checkpoint "ralph: verified completion"; then
      python3 "$SCRIPT_DIR/ralph-update-state.py" mark-blocked "Checkpoint refused; staged work is preserved"
      exit 1
    fi
    exit 0
  fi
  python3 "$SCRIPT_DIR/ralph-compact.py"
  cmd=("$CODEX_BIN" exec --sandbox "$SANDBOX" --json)
  if ! git -C "$REPO_ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then cmd+=(--skip-git-repo-check); fi
  if [ "${#model_args[@]}" -gt 0 ]; then cmd+=("${model_args[@]}"); fi
  prompt="Use the longtask-ralph skill. Read the task contract and the host-selected current_task.md. Process exactly that one atomic task, verify it and record actual evidence. Do not select a different task, expand authority or weaken acceptance. Git initialization and checkpoints are host-controlled opt-in features: do not stage, commit, change identity or ignore files yourself. Mark completion only as a candidate; the host verifier and task/report/blocker gate decide DONE. Continue within scope or report an exact blocker."
  set +e
  "${cmd[@]}" "$prompt" > ".ralph/logs/$label.jsonl" 2> ".ralph/logs/$label.stderr.log"
  result=$?
  set -e
  if [ "$result" -ne 0 ]; then
    python3 "$SCRIPT_DIR/ralph-update-state.py" mark-blocked "Configured CLI failed in $label"
    exit 1
  fi
  python3 "$SCRIPT_DIR/ralph-update-state.py" ensure-state
  verify "$label"
  completion="$(field completion)"
  if [ "$completion" = "RALPH_DONE" ]; then
    python3 "$SCRIPT_DIR/ralph-host.py" finish
    if ! python3 "$SCRIPT_DIR/ralph-host.py" checkpoint "ralph: verified completion"; then
      python3 "$SCRIPT_DIR/ralph-update-state.py" mark-blocked "Checkpoint refused; staged work is preserved"
      exit 1
    fi
    exit $?
  fi
  if [ "$completion" = "RALPH_BLOCKED" ] || [ "$(field status)" = "blocked" ]; then exit 1; fi
  if ! python3 "$SCRIPT_DIR/ralph-host.py" checkpoint "ralph: $label"; then
    python3 "$SCRIPT_DIR/ralph-update-state.py" mark-blocked "Checkpoint refused; user-owned staged work is preserved"
    exit 1
  fi
  if [ "$(field verifier_failures)" -ge 3 ]; then
    python3 "$SCRIPT_DIR/ralph-update-state.py" stop-verifier-failure "Verifier failed three consecutive rounds"
    exit 1
  fi
  if [ "$count" -lt "$MAX_ITERATIONS" ]; then sleep "$SLEEP_SECONDS"; fi
done
python3 "$SCRIPT_DIR/ralph-update-state.py" stop-max-iterations "Reached the configured iteration limit"
