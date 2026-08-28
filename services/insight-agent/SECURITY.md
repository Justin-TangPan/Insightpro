# Insight-Agent Security

## 隔离的可写 Workspace

Insight-Agent 可以修改独立 Workspace，但没有生产写权限。边界由多层共同保证，而不是依赖提示词：

1. 独立 Workspace 不包含 `.env`，也不是生产部署目录。
2. Hermes 只启用文件工具，写入由 `HERMES_WRITE_SAFE_ROOT` 和文件系统权限共同限制；Terminal、Web、Browser、Cron 等工具关闭。
3. Hermes 子进程按用户使用独立非 root UID；Runtime Manager 仅保留创建和切换这些 UID 所需的 capability，根文件系统只读且不挂载 Docker Socket。
4. 不挂载 InsightPro PostgreSQL、生产目录、Service Role、SMTP 或生产 `.env`。
5. Gateway 是唯一发布端口，未授权请求不能直达 Hermes Dashboard。

允许的能力是读取、列举、grep/glob、分析和修改 Workspace 内非敏感项目资料。虽然 Provider API Key 是 Runtime 调用模型所必需的进程凭据，但 Agent 没有 Shell，也不能读取 Workspace 外路径，无法通过正常工具取得它。

## API 与 Terminal

Insight-Agent 不获得 InsightPro API Token，不调用业务 API，因此不能写 Solution、Requirement 或数据库。Bash/Terminal Agent 工具继续禁用；仅把命令设为“ask”并不安全，因为用户批准后仍可能读取 Runtime Secret 或越过 Workspace 边界。

## 身份和点击劫持

Gateway 使用短时一次性 Ticket、可撤销 HttpOnly Cookie 和服务端验证。嵌入响应通过 CSP `frame-ancestors` 只允许配置的 InsightPro Origin。退出 InsightPro 会撤销该用户全部 Gateway Session。

## 多用户隔离

Gateway 不能自行提供数据隔离，因此 Runtime Manager 为每个稳定 `user_id` 启动独立 Hermes Dashboard 子进程，并分配独立 Linux UID、端口、Workspace 和 `HERMES_HOME`。普通用户目录为所有者可写、管理组可管理，其他 UID 无访问权；每位管理员也使用独立 UID，仅加入受限管理组。公共知识库由该管理组可写、普通用户只有读取权限。

管理员的最高权限只存在于该容器已挂载的 AI 空间目录中，不代表宿主机 root。当前 Provider 凭据仍由同一受限 Runtime 服务管理；若未来允许用户自带 Provider Key，应增加独立凭据代理或每用户加密存储。当前尚无面向管理员的 Session 删除专用面板，管理员通过目标用户的原生工作区管理其 Session。

被禁用成员在 Ticket 签发与 Gateway 校验两端都会被拒绝，现有 Gateway Session 同时撤销；其 Workspace 和 Session 保留以防误删。Admin 审计仅记录管理动作；用量计数来自 Runtime 实际请求，Provider 未提供的 Token 不会猜测。
