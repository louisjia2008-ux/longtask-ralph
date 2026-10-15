# Changelog

## 0.1.0 — prerelease

- Package the `longtask-ralph` skill, templates, references and CLI helpers independently.
- Default Git initialization and commits to off, protect repository boundaries and existing staged work, and preserve configured identity.
- Reject initialization over an existing run and require explicit resume without a replacement goal.
- Check verifier results, required task completion, blockers and final report before accepting `RALPH_DONE`.
- Select eligible tasks by priority, then pending/retry status and task ID.
- Add offline fixture tests, installation documentation, MIT licensing, privacy/security guidance and an allowlisted release ZIP builder.

Real Codex runs, provider behavior, long-duration operation and all project toolchains are separate acceptance surfaces.
