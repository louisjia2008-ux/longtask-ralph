# Verifier Strategy

The verifier checks whether the repository still works after one iteration. It prevents Ralph from relying on narrative confidence.

## Result Levels

- `PASS`: required checks passed.
- `SOFT_WARNING`: checks were incomplete or found non-fatal issues; exit 0.
- `FAIL`: checks failed; exit 1.

## Custom Verifier

If `.ralph/custom-verify.sh` exists, run it first. It should contain project-specific commands. A custom verifier may be the strongest signal, but the default verifier can still run extra static checks when useful.

## Project Detection

Common detection:

- `package.json`: Node / JS / TS.
- `pyproject.toml`, `requirements.txt`, `setup.py`: Python.
- `Cargo.toml`: Rust.
- `go.mod`: Go.
- `pom.xml`: Java / Maven.
- `project.godot`: Godot.
- `Makefile`: Make-based projects.
- Markdown-heavy repositories: documentation projects.

## Failure Handling

On verification failure:

1. Record the failing command and a short summary.
2. Mark the task `failed_retryable` if a safe retry exists.
3. Mark it `failed_blocked` if attempts are exhausted or the failure requires human input.
4. Block with `RALPH_BLOCKED` after 3 consecutive verifier failures.

## Human Review

Use human review when the result depends on visual quality, editorial judgment, external systems, accounts, credentials, production behavior, or tools unavailable in the current environment.
