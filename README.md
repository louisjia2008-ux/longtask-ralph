# longtask-ralph

面向 Codex CLI 的长任务 skill 与 shell runner。每轮处理一个明确任务，把任务契约、队列、验证与进度保存在目标项目的 `.ralph/` 中，再按状态继续或停止。

**0.1.0 是预发布版本。** 默认关闭 Git 初始化和自动 commit；真实运行会调用你配置的 Codex CLI，消耗账号额度，并遵守该 CLI 的认证、模型和审批设置。建议先在隔离项目中用一轮任务试用。

## 安装与使用

需要 Bash、Python 3.10+、Git、已安装并配置好的 Codex CLI，以及常见 shell 命令。项目验证还可能需要 npm、pytest、Cargo、Go、Maven、Make 或 Godot；未安装的可选工具不代表对应项目已经验证。

按 [安装说明](docs/INSTALL.md) 复制到用户的 `~/.agents/skills/longtask-ralph/`，或项目的 `.agents/skills/longtask-ralph/`。安装只复制文件，不运行任务；现有安装须由你审查后手动处理，不能直接覆盖。

在目标项目目录中，首次尝试：

```bash
MAX_ITERATIONS=1 AUTO_GIT_INIT=0 AUTO_COMMIT=0 \
  ~/.agents/skills/longtask-ralph/scripts/ralph-start.sh "修复一个明确的失败测试，并记录验证结果"
```

恢复同一次任务时不再传新目标：

```bash
MAX_ITERATIONS=1 ~/.agents/skills/longtask-ralph/scripts/ralph-start.sh
```

使用 skill 时可以写：`Use $longtask-ralph to complete this scoped repository task: <goal>`。直接调用脚本与让 Codex 读取 skill 是两种入口；都应先明确范围与验收标准。

## 运行过程

1. Phase 0 写入目标、验收、非目标、文件范围、风险与 Git 策略。
2. 每轮选择一个依赖已满足的任务，执行后运行项目 verifier。
3. 更新任务、状态、进度和 heartbeat。checkpoint 选项只在明确开启时生效。
4. `RALPH_CONTINUE` 继续；`RALPH_BLOCKED` 停止并说明需要处理的条件。`RALPH_DONE` 必须通过 host 完成检查，模型输出这个标记本身不足以完成任务。

查看 [中文使用说明](docs/LONGTASK_RALPH_USAGE.md)、[安全边界](SECURITY.md) 和 [隐私说明](PRIVACY.md)。

## 边界与默认值

| 选项 | 默认 | 含义 |
|---|---|---|
| `AUTO_GIT_INIT` | `0` | 不初始化仓库 |
| `AUTO_COMMIT` | `0` | 不创建 commit，也不为 checkpoint 修改 Git 配置、index、identity 或 ignore |
| `MAX_ITERATIONS` | `80` | 本次 runner 的最大轮数；首次建议用 `1` |
| `MAX_HOURS` | 未设置 | 只在轮次之间检查；不终止正在运行的 Codex 或 verifier |
| `SANDBOX` | `workspace-write` | 传给 Codex CLI，具体权限由 CLI 与运行环境决定 |

runner 的 Git 保护与完成检查是确定性的；模型执行和自定义 verifier 仍可运行项目命令。此工具不是 OS 隔离层，不拦截所有 shell 命令，也没有金额上限。`MAX_HOURS` 不是硬超时。暂停、CLI 认证或审批可能需要你处理；离线测试不证明无人值守长跑或真实模型效果。

开启 `AUTO_COMMIT=1` 前，目标必须是独立且干净的 Git root，包含正确 identity，暂存区与未跟踪文件都需审查。每次 checkpoint 都拒绝预先存在的 staged 内容。不要在同一目标中同时运行多个 runner。

## 开发与发布包

```bash
python3 -B -m unittest discover -s tests -v
python3 scripts/build-release.py --output /tmp/longtask-ralph-release
```

测试使用临时项目与假 `CODEX_BIN`，不会调用真实模型。ZIP 只有一个 `longtask-ralph/` 根目录，包含 skill、MIT LICENSE 和安装说明；不包含实际 `.ralph`、任务日志、旧 `ralph-codex` 或开发工作区。

## English brief

`longtask-ralph` is a filesystem-backed task loop for Codex CLI. It performs one scoped task per iteration, verifies the project, persists progress, and resumes from `.ralph/`. Git initialization and commits are opt-in. A completion marker is checked by the host against verifier results, task state, blockers, and the final report.

Version 0.1.0 is a prerelease. Start with one iteration in an isolated project. Real runs use your configured Codex account and quota. Shell tools and project verifiers execute commands; the runner is not an operating-system security boundary, cost limiter, or hard deadline controller. See [installation](docs/INSTALL.md), [security](SECURITY.md), and [privacy](PRIVACY.md).

MIT, copyright 2026 louisjia2008-ux. This is an independent project, not an official OpenAI product.
