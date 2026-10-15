# Installation / 安装

Installation copies the skill and its MIT license. It does not initialize a task or invoke Codex. Do not overwrite an existing installation: review and move it yourself first.

## From the source repository

Run these commands from this repository root. User installation:

```bash
skill_source="$PWD/.agents/skills/longtask-ralph"
skill_target="$HOME/.agents/skills/longtask-ralph"
if [ -e "$skill_target" ] || [ -L "$skill_target" ]; then
  echo "Existing installation; review it before replacing." >&2
  exit 1
fi
mkdir -p "$(dirname "$skill_target")"
cp -R "$skill_source" "$skill_target"
cp LICENSE "$skill_target/LICENSE"
```

For project installation, set `skill_target` to the target project's `.agents/skills/longtask-ralph` instead. Keep the MIT license with the copied skill.

## From the release ZIP

Extract the archive into a temporary directory and inspect `longtask-ralph/`. It contains `SKILL.md`, the supporting skill files, `LICENSE`, and `INSTALL.md` under one root. Set `skill_source` to that extracted directory and copy it to the destination using the same existing-path checks above. The extracted directory already includes its license; no separate license copy is needed.

## First run

Open a terminal in the project you intend to work on. Set a small round limit:

```bash
MAX_ITERATIONS=1 AUTO_GIT_INIT=0 AUTO_COMMIT=0 \
  "$HOME/.agents/skills/longtask-ralph/scripts/ralph-start.sh" "A concrete, bounded task"
```

This invokes your configured Codex CLI and consumes account quota. Installation alone does not. To use a different current directory, set `RALPH_REPO_ROOT` explicitly. Resume an existing run with the same command and no goal; a supplied replacement goal is refused to protect existing state.

The source layout is `.agents/skills/longtask-ralph`. The installable ZIP flattens that skill into the single `longtask-ralph` root; it does not include repository tests or runtime records.
