# Insight-Agent Security

## 默认只读

本阶段只需要理解项目并提供建议，不需要生产写权限。只读由多层共同保证，而不是依赖提示词：

1. 独立 Workspace 不包含 `.env`，并以 Docker `:ro` 挂载。
2. OpenCode 配置拒绝 `edit`、`bash`、`task`、`external_directory`、`webfetch` 和 `websearch`。
3. OpenCode 容器使用非 root UID 10002、只读根文件系统、移除全部 Linux capabilities，且不挂载 Docker Socket。
4. 不挂载 InsightPro PostgreSQL、生产目录、Service Role、SMTP 或生产 `.env`。
5. Gateway 是唯一发布端口，未授权请求不能直达 OpenCode。

允许的能力是读取、列举、grep/glob 和分析 Workspace 内非敏感项目资料。虽然 Provider API Key 是 Runtime 调用模型所必需的进程凭据，但 Agent 没有 Shell，也不能读取 Workspace 外路径，无法通过正常工具取得它。

## API 与 Terminal

Insight-Agent 不获得 InsightPro API Token，不调用业务 API，因此不能写 Solution、Requirement 或数据库。OpenCode 的 Bash/Terminal Agent 工具完全禁用；仅把命令设为“ask”并不安全，因为用户批准后仍可绕过只读边界。

## 身份和点击劫持

Gateway 使用短时一次性 Ticket、可撤销 HttpOnly Cookie 和服务端验证。嵌入响应通过 CSP `frame-ancestors` 只允许配置的 InsightPro Origin。退出 InsightPro 会撤销该用户全部 Gateway Session。

## 多用户现状

认证已经完成，但多租户隔离没有完成。OpenCode 单实例会共享 Session、Workspace、配置和凭据，因此当前只允许一个指定管理员。不得通过扩大邮箱名单开放第二位用户。

未来开放写权限或多用户前必须同时具备：每用户独立 Runtime/持久化/Workspace、用户级配额和回收、独立凭据或安全凭据代理、API 最小权限、写操作审计、可恢复快照、明确审批流程，以及针对跨用户 Session/文件访问的自动化隔离测试。
