# Ralph Task Brief

## 1. User Goal

Restate the user's true goal in your own words. Explain the intent behind the surface request, not only the literal wording.

## 2. Final Deliverable

Define the concrete final deliverable, such as:

- runnable code
- fixed bug
- new feature
- workflow file
- prompt template
- documentation
- test report
- acceptance report

## 3. Success Criteria

List specific, checkable completion criteria. Avoid vague language.

## 4. Non-Goals

List what this run will explicitly not do. Use this section to prevent scope creep.

## 5. Constraints

- Do not break existing behavior.
- Do not delete user files.
- Do not rewrite unrelated modules.
- Changes must be recoverable.
- Prefer minimal edits.
- Explain all important changes.
- Test whenever a meaningful test is available.

## 6. Assumptions

List assumptions that are currently unknown but required to continue safely.

## 7. Risk Areas

List likely causes of failure, drift, or unsafe changes.

## 8. Execution Plan

### Phase 1 — Repository / Workspace Safety Check

- Goal:
- Files to modify/create:
- Acceptance method:
- Failure rollback plan:

### Phase 2 — Outline and Plan

- Goal:
- Files to modify/create:
- Acceptance method:
- Failure rollback plan:

### Phase 3 — Incremental Execution

- Goal:
- Files to modify/create:
- Acceptance method:
- Failure rollback plan:

### Phase 4 — Verification

- Goal:
- Files to modify/create:
- Acceptance method:
- Failure rollback plan:

### Phase 5 — Final Acceptance Report

- Goal:
- Files to modify/create:
- Acceptance method:
- Failure rollback plan:

## 9. Drift Guard

- After each phase, reread this task brief.
- If the current action does not serve the User Goal or Success Criteria, stop.
- If the goal must change, update this task brief first.
- Do not expand scope without explaining why and recording the change here.

## 10. Git Safety

- Before starting task work, check whether the current directory is a git repo.
- If it is not a git repo, run `git init`.
- Create `.gitignore` if missing.
- Leave Git automation off by default. If explicitly enabled, require the exact target root, configured identity and a clean start; preserve existing staged work.
- Create one commit after each completed phase.
- Commit messages must include the Ralph phase name.
- If the task fails, explain how to roll back to the previous safe commit.
