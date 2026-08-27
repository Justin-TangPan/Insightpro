# Insight-Agent Architecture

```text
Browser / InsightPro shell
  └─ persistent Insight-Agent iframe
       └─ Auth Gateway :4096
            ├─ InsightPro FastAPI SSO verification
            └─ Runtime Manager :4096 (internal only)
                 └─ OpenCode child process / user_id
                      ├─ private Workspace + Session store
                      └─ shared public knowledge
```

## 服务和网络

InsightPro 前后端继续由根 Compose 管理。Insight-Agent Runtime Manager 与 Gateway 使用独立 `insight-opencode` Compose project 和 Docker network；主系统部署、`--remove-orphans`、readiness 与 full health 不管理它。宿主机只发布 Gateway，各用户 OpenCode 子进程仅监听 Runtime 容器回环地址。

## UI 和 Session

`InsightAgentShell` 在 Next.js 根布局内持久挂载。浮窗、最大化、还原和 `/insight-agent` 完整页只改变同一 iframe 的尺寸与位置，不替换 iframe，因此浏览器页面状态和当前 Session 不重置。OpenCode Session/消息持久化在独立数据目录中。

## 用户和认证

Supabase Auth 是唯一身份源。前端以 Supabase access token 向同源 InsightPro API 换取 60 秒一次性 Ticket；Gateway callback 消费 Ticket 后建立可撤销 HttpOnly Session。Gateway 每次请求向 FastAPI 验证并取得可信 `user_id`、身份角色和目标空间，Runtime Manager 再按 `user_id` 路由。用户退出 InsightPro 时立即撤销。只有管理员可签发指向其他用户空间的 Ticket。

## 数据与安全边界

- `spaces/<user_id>/workspace`：用户独立、可写的 Git Workspace，不包含生产 `.env`。
- `spaces/<user_id>/{data,state,cache,config}`：独立持久化的 Session 和运行状态。
- `/knowledge/public`：公共知识库；普通用户只读，管理员读写。
- OpenCode config：按普通用户/管理员生成；允许授权目录内 edit，拒绝 bash、task 和 web 工具。
- InsightPro PostgreSQL、Docker Socket、生产目录和生产 `.env`：不挂载、不联网授权。
- OpenCode 与 InsightPro 业务 API/数据库无调用关系。

普通用户子进程使用独立 Linux UID；用户目录不可被其他普通 UID 遍历。管理员子进程使用受限管理 UID，可维护所有空间，但容器未挂载生产目录、Docker Socket 或生产 Secret。Runtime Manager 只承担目录配置、子进程生命周期和代理，不访问 InsightPro 数据库。
