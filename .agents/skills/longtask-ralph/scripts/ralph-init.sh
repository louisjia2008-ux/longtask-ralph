#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="${RALPH_REPO_ROOT:-$(pwd -P)}"
cd "$REPO_ROOT"
REPO_ROOT="$(pwd -P)"
SANDBOX="${SANDBOX:-workspace-write}"
CODEX_BIN="${CODEX_BIN:-codex}"
MODEL_ARGS="${MODEL_ARGS:-}"
AUTO_GIT_INIT="${AUTO_GIT_INIT:-0}"
AUTO_COMMIT="${AUTO_COMMIT:-0}"
export AUTO_GIT_INIT AUTO_COMMIT
if [ "${1:-}" = "--help" ] || [ "${1:-}" = "-h" ]; then
  echo "Usage: ralph-init.sh goal; Git initialization and commits default to off."
  exit 0
fi
if [ "$#" -eq 0 ]; then echo "A concrete goal is required." >&2; exit 1; fi
python3 "$SCRIPT_DIR/ralph-host.py" preflight-init
python3 - "$*" "$SCRIPT_DIR" <<'PY_INIT'
import json, sys
from datetime import datetime, timezone
from pathlib import Path
root = Path.cwd()
ralph = root / '.ralph'
ralph.mkdir()
for name in ('logs', 'artifacts', 'snapshots'):
    (ralph / name).mkdir()
goal, script_dir = sys.argv[1:]
now = datetime.now(timezone.utc).isoformat()
(ralph / 'goal.md').write_text('# Goal\n\n' + goal + '\n')
for source, target in [('task_brief.md', 'task_brief.md'), ('progress_log.md', 'progress_log.md'), ('acceptance_report.md', 'acceptance_report.md')]:
    (ralph / target).write_bytes((Path(script_dir).parent / 'templates' / source).read_bytes())
with (ralph / 'task_brief.md').open('a') as out:
    out.write('\n## Raw user goal\n\n' + goal + '\n')
for name, text in [('acceptance.md', 'Phase 0 must write concrete acceptance criteria.'), ('plan.md', 'Phase 0 must write the scoped plan.'), ('verifier.md', 'Phase 0 must choose project-specific verification.'), ('progress.md', '# Progress\n\nInitialization planning is pending.'), ('heartbeat.md', '# Heartbeat\n\nInitialization planning is pending.'), ('current_task.md', '# Current task\n\nPlanning the goal.')]:
    (ralph / name).write_text(text + '\n')
(ralph / 'custom-verify.sh').write_text('#!/usr/bin/env bash\necho "SOFT_WARNING: Replace this placeholder verifier with project-specific checks."\n')
(ralph / 'custom-verify.sh').chmod(0o755)
state = {'version': '0.1', 'status': 'planning', 'completion': 'RALPH_CONTINUE', 'current_iteration': 0, 'blockers': [], 'started_at': now, 'updated_at': now}
tasks = {'version': '0.1', 'status': 'planning', 'goal_summary': goal, 'tasks': [{'id': 'T001', 'title': 'Lock the goal and verification plan', 'status': 'pending', 'priority': 'high', 'dependencies': [], 'attempts': 0}], 'blockers': []}
(ralph / 'state.json').write_text(json.dumps(state, indent=2) + '\n')
(ralph / 'tasks.json').write_text(json.dumps(tasks, indent=2) + '\n')
PY_INIT
model_args=()
if [ -n "$MODEL_ARGS" ]; then read -r -a model_args <<< "$MODEL_ARGS"; fi
cmd=("$CODEX_BIN" exec --sandbox "$SANDBOX")
if ! git -C "$REPO_ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then cmd+=(--skip-git-repo-check); fi
if [ "${#model_args[@]}" -gt 0 ]; then cmd+=("${model_args[@]}"); fi
prompt="Use the longtask-ralph skill. Complete Phase 0 planning only: read the goal and task brief, lock scope and acceptance, create atomic tasks, and replace the placeholder verifier with relevant checks. Do not implement the main task. Git automation is opt-in; do not initialize, stage, commit, change identity or ignore files yourself when it is off. Preserve the user's authorization boundaries. Leave completion as RALPH_CONTINUE."
"${cmd[@]}" "$prompt" 2> .ralph/logs/init.stderr.log | tee .ralph/logs/init.stdout.log
python3 "$SCRIPT_DIR/ralph-update-state.py" ensure-state
python3 "$SCRIPT_DIR/ralph-host.py" planning-complete
python3 "$SCRIPT_DIR/ralph-host.py" checkpoint "ralph: Phase 0 Mission Lock"
echo "Phase 0 recorded. Resume through ralph-start.sh without another goal."
