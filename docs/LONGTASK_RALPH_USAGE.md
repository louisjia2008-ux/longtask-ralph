# longtask-ralph 使用说明

本工具把长任务拆成多次 Codex CLI 执行，用目标项目的 `.ralph/` 保存契约、任务和验证。每轮只处理一项工作。真实运行会消耗 Codex 账号额度；安装和离线测试不调用模型。

## 安装与第一次运行

按 [INSTALL.md](INSTALL.md) 安装到用户 `~/.agents/skills/longtask-ralph` 或目标项目的 `.agents/skills/longtask-ralph`。不要覆盖已有安装。保留随附 MIT LICENSE。

在目标项目目录中首次试用：

```bash
MAX_ITERATIONS=1 AUTO_GIT_INIT=0 AUTO_COMMIT=0 \
  "$HOME/.agents/skills/longtask-ralph/scripts/ralph-start.sh" "修复一个明确的失败测试并验证"
```

先准备已认证、配置好的 Codex CLI。运行可能依据 CLI 设置要求审批。脚本不帮助绕过审批，也不需要把凭据保存在 skill 中。

## 初始化和恢复

没有 `.ralph/` 时，start 调用 init 建立 Phase 0 任务契约，再进入执行。已有状态时，不传目标即可恢复。传入新目标会被拒绝，以免把新目标默默当作旧目标继续。直接 init 也拒绝已有运行；需要新目标时，先自行审查并归档旧状态。

从其他目录运行可设 `RALPH_REPO_ROOT`。目标不能意外落入祖先 Git 仓库。每个目标同时只运行一个 runner。

## 默认参数

| 参数 | 默认 | 说明 |
|---|---|---|
| `MAX_ITERATIONS` | `80` | 当前启动最多执行多少轮，试用设 `1` |
| `MAX_HOURS` | 空 | 仅在轮次之间检查，不会杀掉已启动的子进程 |
| `SLEEP_SECONDS` | `5` | 轮次间隔 |
| `SANDBOX` | `workspace-write` | 传给 CLI；有效权限由 CLI 和 host 决定 |
| `AUTO_GIT_INIT` | `0` | 显式设 `1` 才可初始化 |
| `AUTO_COMMIT` | `0` | 显式设 `1` 才可做 checkpoint |
| `NO_DIFF_LIMIT` | `3` | 诊断 warning 阈值，不是单独停止条件 |
| `CODEX_BIN` | `codex` | 可信 Codex 可执行文件；测试用替身 |
| `MODEL_ARGS` | 空 | 可信操作者提供的 CLI 参数，不读取不可信项目文本 |

没有金额上限，也没有单次调用的硬超时。终端中 `Ctrl+C` 停止 runner 后应检查子进程和 `.ralph` 状态，再恢复。

## Git checkpoint

默认不初始化、不提交，也不修改 Git config、index、ignore 或 identity。开启自动 checkpoint 前，目标必须是独立 Git root，使用者先设置好 identity，工作区须干净，包括未跟踪文件。已有 staged 内容必须自行处理，runner 不会代替你提交。

每次 checkpoint 都会拒绝预先存在的 staged 内容，保留已有 identity。运行期间也不要在另一个终端暂存文件。checkpoint 是本地恢复记录，不会自动 push 或部署。`.ralph/` 可能包含私人目标和模型/工具输出，启用 commit 前必须审查 ignore 规则。

## 验证与完成

默认 verifier 运行自定义 `.ralph/custom-verify.sh` 和检测到的项目检查；这些是实际 shell 命令，可能写构建产物或联网。先审查项目脚本。缺少可选验证工具必须作为未验证限制记录。

模型写出 `RALPH_DONE` 不代表成功。host 还会检查最新 verifier、required tasks、非空最终报告和 blocker。`human_review_needed` 仍是未完成的人审事项，不能伪装成已通过。

查看状态：

```bash
"$HOME/.agents/skills/longtask-ralph/scripts/ralph-status.sh"
```

`RALPH_CONTINUE` 表示在限制内继续，`RALPH_BLOCKED` 表示先处理明确阻碍。完成状态只能在 host gate 通过后接受。

## 数据与边界

`.ralph/` 的 goal、tasks、logs、heartbeat、snapshots 和 final report 都是本地任务数据。不要直接公开。安全说明见仓库 SECURITY.md，隐私说明见 PRIVACY.md。

skill 规则与 runner 检查不是 OS 安全隔离。模型执行、自定义 verifier、同权限进程与使用者提供的 CLI 参数都在信任边界内。离线 fake CLI 测试不能证明真实模型质量、无人值守多小时恢复或所有平台工具链兼容。
