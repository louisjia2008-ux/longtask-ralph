# Ralph Protocol

Ralph is a long-running task loop for Codex CLI. An external shell runner repeatedly invokes `codex exec`, and each invocation performs one bounded task checkpoint. The runner continues automatically while state is `RALPH_CONTINUE`.

Before the loop may execute project work, Ralph must complete Phase 0: Mission Lock. Phase 0 writes `.ralph/task_brief.md`, which is the task contract and drift guard for the run.

## Ralph Loop

The loop is:

0. Confirm `.ralph/task_brief.md` exists and the current action serves it.
1. Read durable state from `.ralph/`.
2. Select one atomic task.
3. Execute only that task.
4. Verify the repository state.
5. Update `.ralph/`.
6. Create a checkpoint.
7. Continue automatically on `RALPH_CONTINUE`, stop only on `RALPH_DONE` or `RALPH_BLOCKED`.

## Phase 0 Mission Lock

Phase 0 must run before code edits, generated project files, or refactors. It defines:

- user goal
- final deliverable
- success criteria
- non-goals
- constraints
- assumptions
- risk areas
- phased execution plan
- drift guard
- git safety

If the task brief is missing, Ralph creates or repairs it and continues to Phase 1. If the next action would drift from it, Ralph writes `RALPH_BLOCKED` with the blocker reason.

## Why Fresh Execution

Fresh execution prevents a multi-hour task from depending on a single growing context. Any iteration can crash, time out, or be interrupted, and the next run can recover by reading `.ralph/`.

## Why State Exists In `.ralph/`

`.ralph/` is the control plane. It stores the task brief, goal, acceptance criteria, plan, task queue, progress log, heartbeat, verifier notes, blockers, snapshots, and final report. The state must be readable by a future fresh Codex execution.

## Why One Task Per Iteration

One atomic task keeps diffs small, makes verification meaningful, and gives git checkpoints a useful granularity. It also limits damage when a task was misunderstood.

This does not mean the long run waits for the user after every task. It means each `codex exec` invocation has a bounded unit of work; the runner invokes the next unit automatically while `.ralph/state.json` remains `RALPH_CONTINUE`.

## Why Verifier

A long-running agent must not claim success by narration. It must run checks and record results. Verification can be a custom script, project-specific tests, or static sanity checks.

## Why Stop Conditions

Stop conditions keep autonomy bounded. Repeated failures, dangerous operations, missing context and sandbox limits stop the run with a written blocker. No-diff is diagnostic, not by itself a stop condition.

`RALPH_CONTINUE`, checkpoint completion, git commit completion, phase completion, and a printed Next task are not stop conditions.

## Why Not Infinite Autonomy

Long-running does not mean unlimited permission. Ralph must obey `MAX_ITERATIONS`, repository boundaries and user scope. Optional `MAX_HOURS` is checked between rounds; it is not a hard deadline or spending limit. The host checks verifier/task/report/blocker evidence before accepting a model-written DONE.
