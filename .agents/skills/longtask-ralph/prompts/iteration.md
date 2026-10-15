# Ralph Iteration Prompt

Use the longtask-ralph skill.

You are inside a Ralph long-running execution loop.

Perform the next atomic task for this runner invocation. The runner continues automatically while state is `RALPH_CONTINUE`; do not treat `RALPH_CONTINUE`, checkpoint completion, git commit completion, or a printed Next task as a user-confirmation pause.

Rules:

1. Read `.ralph/task_brief.md` first.
2. Read all `.ralph/` state files.
3. Confirm the selected action serves the User Goal and Success Criteria.
4. If resuming from `RALPH_CONTINUE`, select exactly one next atomic task.
5. Write the selected task to `.ralph/current_task.md`.
6. Implement only that task.
7. Run the relevant verifier.
8. Update `.ralph/tasks.json`.
9. Update `.ralph/state.json`.
10. Append to `.ralph/progress.md` and `.ralph/progress_log.md` if present.
11. Append to `.ralph/heartbeat.md`.
12. If complete, write `.ralph/final_report.md` from `templates/acceptance_report.md` and set completion to `RALPH_DONE`.
13. Do not push.
14. Do not deploy.
15. Do not delete large directories.
16. Do not run git rebase, git reset, git clean, or git filter-branch.
17. Use `RALPH_CONTINUE` only to mean "continue automatically to the next task"; use `RALPH_DONE` only when all acceptance criteria are complete; use `RALPH_BLOCKED` only when user or external action is required.

Output:

Current task:
What changed:
Verification:
Commit:
Files changed:
State updated:
Drift guard:
Next task:
Status:
Action:
