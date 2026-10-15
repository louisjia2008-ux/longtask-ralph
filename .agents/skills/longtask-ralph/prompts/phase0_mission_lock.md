# Phase 0 Mission Lock Prompt

Use the longtask-ralph skill.

You are performing Phase 0 — Mission Lock / Task Contract / 任务目标锁定.

This phase must happen before implementation, file generation outside `.ralph/`, or project refactoring.

User goal:
<USER_GOAL>

You must:

1. Inspect the repository/workspace enough to understand context.
2. Create or update `.ralph/task_brief.md`.
3. Use the exact sections from `templates/task_brief.md`.
4. Restate the user's real goal in your own words.
5. Define final deliverables.
6. Define concrete success criteria.
7. Define non-goals and constraints.
8. List assumptions and risk areas.
9. Create a phased execution plan with continue / stop / rollback judgment for every phase.
10. Record Git safety expectations.
11. Do not implement the main task yet.
12. End with `RALPH_CONTINUE` unless Phase 0 is blocked.
13. Include `Action: Continuing automatically to Phase 1` when status is `RALPH_CONTINUE`; Phase 0 checkpoint is not a user-confirmation pause.

Output:

Current phase:
Task brief:
Drift guard:
Git safety:
Next phase:
Status:
Action:
