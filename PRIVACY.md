# Privacy

The project does not add an analytics endpoint. A real run invokes the configured Codex CLI; that service and your account settings govern model processing. Project verification commands may have their own network behavior.

`.ralph/` can contain goals, repository details, prompts, model/tool output, errors, changed paths, snapshots and final reports. Treat it as private runtime state. The host excludes `.ralph/` from its checkpoint commits. Your own Git commands or other tools can still add these records to history, so review ignore rules and staged content before publishing any project.

Do not paste credentials into goals, templates or custom verification scripts. Do not include real task records in bug reports. Use synthetic fixtures, remove private paths and inspect Git history as well as current files before sharing.

Release artifacts are built from an explicit source allowlist. They contain no actual `.ralph/` state, model output, credentials, user installation or local configuration. Credential scans cover recognized patterns; they do not prove the absence of personal data, copyright issues or unknown secret formats.
