# Contributing / 贡献

请用合成资料复现问题。不要提交真实 Vault、目标正文、会话、密钥、配置或 `.ralph/` 运行记录。
Use synthetic fixtures. Do not commit private runtime data or credentials.

首次 clone 后显式启用本地上传保护：

```sh
git config core.hooksPath .githooks
python3 scripts/privacy_guard.py
python3 scripts/privacy_guard.py --history
```

pre-commit 检查整个暂存区的实际内容；pre-push 检查所有本地 ref 可达的对象与提交元数据。Hook 可以被绕过，CI 发生在上传之后，因此公开前还必须人工审查源码边界，并用 Gitleaks 检查完整历史及所有发布文件。不要依赖 CI 阻止第一次隐私上传。

本地 guard 只输出文件名和规则，不输出命中的值。扫描报告也应使用完整脱敏。发布包应通过固定白名单打包，并检查 ZIP 内容与 SHA256。真实用户数据不能成为测试 fixture。

请遵循 README 的本地验证命令；测试应在临时目录运行，模型调用默认使用本地 fake，不使用真实 API Key。仓库 GitHub Actions 默认只有 contents: read 权限，发布由维护者明确执行。
