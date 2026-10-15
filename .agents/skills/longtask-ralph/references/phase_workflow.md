# Ralph Phase Workflow

Ralph long tasks run through six phases.

## Phase 0 — Mission Lock / Task Contract / 任务目标锁定

Create `.ralph/task_brief.md` before implementation. This locks the user's goal, deliverable, success criteria, non-goals, constraints, assumptions, risks, execution plan, drift guard, and git safety plan.

Do not enter later phases without a non-empty `.ralph/task_brief.md`.

Decision:

- Continue if the goal, deliverable, success criteria, and boundaries are clear.
- Block with `RALPH_BLOCKED` if the goal is unsafe, contradictory, or missing critical context.
- Roll back only if Phase 0 changed non-state files unexpectedly.

## Phase 1 — Repository / Workspace Safety Check

Confirm the exact target root, preserve repository state, identify project type and record verifier options. Git initialization and checkpoint commits are opt-in; disabled automation must not modify Git metadata or ignore rules.

Decision:

- Continue if the workspace is recoverable and verifier strategy is known.
- Block with `RALPH_BLOCKED` if secrets, destructive requirements, or missing permissions block safe execution.
- Stop and report unexpected setup changes; do not automatically reset user work.

## Phase 2 — Outline and Plan

Write `.ralph/plan.md`, `.ralph/acceptance.md`, and `.ralph/tasks.json` with small dependency-aware tasks.

Decision:

- Continue if tasks are atomic and map to success criteria.
- Block with `RALPH_BLOCKED` if the plan no longer matches `.ralph/task_brief.md`.
- Roll back to the previous checkpoint if planning altered project files.

## Phase 3 — Incremental Execution

Execute one atomic task per iteration. Keep edits minimal and scoped.

Decision:

- Continue if the task produced useful progress and verifier output is acceptable.
- Block with `RALPH_BLOCKED` on repeated failures, unresolved drift, or unsafe lack of progress; do not stop merely because a checkpoint finished.
- Roll back to the previous phase checkpoint when the change damages the project.

## Phase 4 — Verification

Run custom or detected verification. Record PASS, SOFT_WARNING, FAIL, and human review needs.

Decision:

- Continue if verification passes or warnings are understood.
- Block with `RALPH_BLOCKED` if verification repeatedly fails.
- Roll back to the last safe checkpoint if the failure is caused by recent changes.

## Phase 5 — Final Acceptance Report

Write final acceptance report from the task brief and verification evidence.

Decision:

- Complete only when success criteria are satisfied or explicitly marked for human review.
- Set `RALPH_DONE` only when complete; keep `RALPH_BLOCKED` if unresolved blockers remain.
- Roll back only if final reporting changed project behavior, which should not happen.
