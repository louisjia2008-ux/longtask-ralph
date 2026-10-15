# Task Contract

## Atomic Task

An atomic task is a single unit of work that can be implemented, verified, and summarized in one iteration. It should have one purpose, a limited file scope, concrete acceptance criteria, and a verification path.

If a task requires multiple independent changes, split it before execution.

## Status Machine

Allowed statuses:

- `pending`: ready when dependencies are done.
- `in_progress`: selected in the current iteration.
- `done`: completed and verified.
- `failed_retryable`: failed but may be retried.
- `failed_blocked`: failed and should not be retried without human input.
- `skipped_with_reason`: skipped with a concrete written reason.
- `human_review_needed`: automated verification is insufficient.

Typical transitions:

- `pending` -> `in_progress`
- `in_progress` -> `done`
- `in_progress` -> `failed_retryable`
- `failed_retryable` -> `in_progress`
- `failed_retryable` -> `failed_blocked`
- non-terminal -> `skipped_with_reason`
- non-terminal -> `human_review_needed`

## Dependencies

Dependencies are task ids. A task may be selected only when every dependency is `done`. If a dependency is skipped or needs human review, the dependent task must be revised, skipped with reason, or blocked.

## Acceptance Criteria

Acceptance criteria must be concrete and checkable. Prefer file existence, command success, test output, documented human review gates, or specific behavior.

Do not weaken acceptance criteria merely to finish. If a criterion cannot be automated, mark it as human review and explain why.

## Attempts And Retry

Each failed attempt increments `attempts`. A task with `attempts >= 3` must not be selected again. On the third failure, add a blocker and set `RALPH_BLOCKED`.

Retries should use new evidence from logs or verification output. Do not repeat the same failing edit blindly.

## Human Review Needed

Use `human_review_needed` for subjective design, UX, content quality, production impact, account permissions, or behavior that cannot be validated in the current sandbox. Human review items must appear in the final report.
