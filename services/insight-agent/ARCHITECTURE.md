# Insight-Agent Architecture

```text
Browser / InsightPro shell
  └─ persistent Insight-Agent iframe
       └─ Auth Gateway :4096
            ├─ InsightPro FastAPI SSO verification
            └─ Runtime Manager :4096 (internal only)
                 └─ Hermes Dashboard child process / user_id
                      ├─ private Workspace + Session store
                      └─ shared public knowledge
```

对象页打开 Insight-Agent 时，浏览器先向 InsightPro API 创建 `agent_session`。Backend 按 `user_id` 读取并过滤业务对象，保存小型 `context_snapshot`，将 Session ID 绑定到 SSO Gateway Session。Runtime 再以内部密钥和可信用户 ID 取得该快照，写入隔离 Workspace 的 `.insight/INSIGHT_CONTEXT.md`；Hermes 从不直接访问业务数据库。

Agent 若要形成业务资产，只能写 `.insight/INSIGHT_ACTION.json` 的白名单 Draft。用户在 InsightPro Shell 读取并确认后，Backend 校验 Action Schema、对象所有权和关联 Requirement，最后复用 Workbench Service 写入 Draft。

## 服务和网络

InsightPro 前后端继续由根 Compose 管理。Insight-Agent Runtime Manager 与 Gateway 使用独立 `insight-hermes` Compose project 和 Docker network；主系统部署和健康检查不管理它。宿主机只发布 Gateway，各用户 Hermes Dashboard 子进程仅监听 Runtime 容器回环地址。

## UI 和 Session

`InsightAgentShell` 在 Next.js 根布局内持久挂载。浮窗、最大化、还原和完整页复用同一 iframe；Hermes Session/消息持久化在用户独立目录中。

## 用户和认证

Supabase Auth 是唯一身份源。前端以 Supabase access token 向同源 InsightPro API 换取 60 秒一次性 Ticket；Gateway callback 消费 Ticket 后建立可撤销 HttpOnly Session。Gateway 每次请求向 FastAPI 验证并取得可信 `user_id`、身份角色和目标空间，Runtime Manager 再按 `user_id` 路由。用户退出 InsightPro 时立即撤销。只有管理员可签发指向其他用户空间的 Ticket。

## 数据与安全边界

- `spaces/<user_id>/workspace`：用户独立、可写的 Git Workspace，不包含生产 `.env`。
- `spaces/<user_id>/{data,state,cache,config}`：独立持久化的 Session 和运行状态。
- `/knowledge/public`：公共知识库；普通用户只读，管理员读写。
- Hermes config：仅启用文件工具；普通用户不能修改工具和系统配置，管理员可维护 AI 空间配置。
- InsightPro PostgreSQL、Docker Socket、生产目录和生产 `.env`：不挂载、不联网授权。
- Hermes 与 InsightPro 业务 API/数据库无写入关系。

每位用户（包括管理员）使用独立 Linux UID；用户目录不可被其他普通 UID 遍历。管理员额外加入受限管理组，可维护 AI 空间与公共知识库，但容器未挂载生产目录、Docker Socket 或生产 Secret。Runtime Manager 只承担目录配置、子进程生命周期和代理，不访问 InsightPro 数据库。

## 运维可见性

Runtime 注册表记录每个用户的启动次数、按日请求数及 Provider 明确返回的 Token。FastAPI 记录 Admin 的成员、Runtime 和公共知识库管理操作到 `agent_audit_events`。这些记录不包含聊天正文、文件内容或 Secret；Insight-Agent 不在 InsightPro readiness 路径中，Runtime 故障不会阻断主系统。

历史 SSO 表和少量配置仍使用 `opencode_*` 名称以兼容已部署数据和回调路径；产品与新代码统一称为 `Insight-Agent` / `AI Space`，该遗留命名不作高风险迁移。
