# Insight-Agent Architecture

```text
Browser / InsightPro shell
  └─ persistent Insight-Agent iframe
       └─ Auth Gateway :4096
            ├─ InsightPro FastAPI SSO verification
            └─ OpenCode Web :4096 (internal only)
                 └─ isolated writable InsightPro Git Workspace
```

## 服务和网络

InsightPro 前后端继续由根 Compose 管理。Insight-Agent Runtime 与 Gateway 使用独立 `insight-opencode` Compose project 和 Docker network；主系统部署、`--remove-orphans`、readiness 与 full health 不管理它。宿主机只发布 Gateway，OpenCode 只在内部网络暴露。

## UI 和 Session

`InsightAgentShell` 在 Next.js 根布局内持久挂载。浮窗、最大化、还原和 `/insight-agent` 完整页只改变同一 iframe 的尺寸与位置，不替换 iframe，因此浏览器页面状态和当前 Session 不重置。OpenCode Session/消息持久化在独立数据目录中。

## 用户和认证

Supabase Auth 是唯一身份源。前端以 Supabase access token向同源 InsightPro API 换取 60 秒一次性 Ticket；Gateway callback 消费 Ticket 后建立 5 分钟 HttpOnly Session。Gateway 对每个请求向 FastAPI 验证 Session，并在内部注入 OpenCode 服务级 Basic Auth。Supabase Token、Basic Auth 和 Provider 密钥都不会进入 URL或下发给 Agent。

## 数据与安全边界

- `/workspace`：独立、可写的 Git Workspace，不包含生产 `.env`；修改不会直接作用于生产仓库。
- OpenCode data/state/cache：独立持久化，允许 Runtime 保存 Session。
- OpenCode config：固定只读配置文件；允许 Workspace 内 edit，拒绝 bash、task、external directory 和 web 工具。
- InsightPro PostgreSQL、Docker Socket、生产目录和生产 `.env`：不挂载、不联网授权。
- OpenCode 与 InsightPro 业务 API/数据库无调用关系。

单 OpenCode 实例的 Session、Workspace、配置和 Provider 凭据没有 InsightPro `user_id` 所有权。本阶段仅允许配置中的唯一管理员。正式多用户需要 Gateway 按 `user_id` 路由到独立 Runtime、数据目录和 Workspace。
