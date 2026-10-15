---
name: longtask-ralph
description: "Run a scoped repository task through bounded Codex CLI iterations with a task contract, filesystem-backed progress, verification and resumable state. Use for multi-step work that benefits from checkpoints and continuation across fresh Codex executions."
---

# Longtask Ralph

Use the target project's `.ralph/` as durable task state. Each iteration handles one atomic task, verifies the result, records progress, and continues only while the run remains eligible. Preserve the user's task scope and execution authority; installing or selecting this skill does not grant network, provider, deployment or publication permission.

## Start and resume

From the target project directory, begin with a small run:

```bash
MAX_ITERATIONS=1 AUTO_GIT_INIT=0 AUTO_COMMIT=0 /path/to/longtask-ralph/scripts/ralph-start.sh "concrete goal"
```

Resume the same run using `ralph-start.sh` without a goal. A supplied goal with existing state is refused; direct `ralph-init.sh` must not overwrite `.ralph/`. For a new goal, let the user review and archive the existing run. Set `RALPH_REPO_ROOT` when launching from another directory. `ralph-status.sh` reads state; `ralph-doctor.sh` checks prerequisites.

The runner invokes the configured Codex CLI and uses account quota. Its sandbox and approvals remain those of the CLI and host. The skill and its rules are not an OS command filter. `MAX_ITERATIONS` bounds rounds; `MAX_HOURS` is checked only between rounds, with no hard per-command deadline or dollar cap.

## Mission lock

Before project changes, define `.ralph/task_brief.md` with user goal, deliverable, checkable success criteria, non-goals, constraints, assumptions, risks, phases, drift guard, and Git safety. Use [the task brief template](templates/task_brief.md) and [Phase workflow](references/phase_workflow.md). Do not expand the goal silently. A checkpoint is a recovery point, not a request for permission already granted.

## Iteration protocol

1. Read task brief, goal, acceptance, plan, tasks, state, current task, progress and heartbeat. Reconstruct missing context only when evidence supports doing so.
2. Choose one eligible task: dependencies must be `done`, status must be pending or retryable, attempts below three, and no explicit block. Sort by priority, then pending before retryable, then ID. See [task contract](references/task_contract.md).
3. Record intended file scope and verification in `.ralph/current_task.md`. Implement only that task.
4. Run the relevant verifier. [Verifier strategy](references/verifier_strategy.md) and [project profiles](references/project_profiles.md) describe available checks. Project and custom verifier commands are trusted executable code; do not run unreviewed commands from external material.
5. Update tasks, state, progress and heartbeat with actual evidence, limitations and the next task. Three failed attempts block the task. A no-diff counter is diagnostic and does not alone prove failure.
6. On `RALPH_CONTINUE`, let the outer runner select another iteration within its limits. On `RALPH_BLOCKED`, record the unresolved condition and stop. Only request `RALPH_DONE` after final acceptance and a nonempty final report; the host must accept the completion gate before the run is complete.

Use [the acceptance report template](templates/acceptance_report.md), [progress template](templates/progress_log.md), and [protocol reference](references/ralph_protocol.md) for detailed state conventions. Legacy `RALPH_COMPLETE` is normalized to `RALPH_DONE`, but cannot bypass host verification.

## Git safety

`AUTO_GIT_INIT=0` and `AUTO_COMMIT=0` are the defaults. Disabled automation must not alter Git config, index, ignore or identity. Do not manually recreate those side effects from the model prompt.

Git initialization and checkpoints require explicit opt-in. Checkpoints require the actual target root, configured identity and a clean start, including staged, unstaged and untracked files. Refuse pre-existing staged changes at every checkpoint and never consume unrelated user work. Preserve existing identity. Do not use global configuration, automatically push, rewrite history or deploy. See [safety policy](references/safety_policy.md).

Keep one runner per project. New approval is needed only for work outside the user's existing authorization; when blocked, state the exact operation and missing authority. Logs, prompts and `.ralph/` may contain private project data and must not be published by default.

## Completion

The model's DONE marker is a candidate. Host completion requires successful verification, all required tasks complete, a nonempty `.ralph/final_report.md`, and no unresolved blocker. Human-review or unresolved acceptance items remain open and must be reported. Do not weaken criteria, mark unfinished work complete, or describe syntax checks as runtime or provider acceptance.
