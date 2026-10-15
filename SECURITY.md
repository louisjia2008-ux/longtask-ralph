# Security and execution boundaries

The runner passes `SANDBOX=workspace-write` to Codex by default. The Codex CLI, its approval configuration and the host determine what that permits. Skill instructions do not create an OS sandbox, network allowlist, spending budget or command interception layer.

Run only in a project you trust. The selected model may edit project files and invoke tools. The custom verifier and detected test/build commands are ordinary shell commands with the runner's permissions. Review them before a run. `CODEX_BIN` and `MODEL_ARGS` are trusted operator settings; do not populate them from untrusted repository text.

## Host protections

- Git initialization and checkpoint commits default to off. Disabled Git automation does not alter Git config, index, identity or ignore files.
- Opt-in Git checkpoints require the actual target root, configured identity and a clean start; existing staged changes are rejected before every checkpoint.
- Existing `.ralph/` state is preserved. Resume through `ralph-start.sh` without a new goal; direct initialization over existing state is refused.
- `RALPH_DONE` is accepted only after host completion checks. This checks machine-readable state, not the truth of every natural-language acceptance claim.

Keep one runner per target. Stop it before manually modifying run state or sharing the project with another process. A local user/process that can change the runner, verifier or state is within the same trust boundary. The project does not claim to resist a malicious process with the same filesystem access.

`MAX_HOURS` is checked between iterations. It does not kill a hung model call, test or child process. There is no hard deadline or monetary cap. Use your own operating-system process controls and account limits where required.

## Reporting

For vulnerabilities or exposed credentials, contact the maintainer privately through GitHub's private vulnerability reporting if available. Do not put credentials, personal task logs or exploit-bearing private data in public issues. Include the version, affected boundary, a synthetic reproduction and the expected behavior. This volunteer prerelease has no response-time SLA.
