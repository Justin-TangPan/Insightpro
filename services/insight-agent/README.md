# Insight-Agent

Insight-Agent 是 InsightPro 内置的 AI 智能工作区，直接复用 [Nous Research Hermes Agent](https://github.com/NousResearch/hermes-agent) 的源码核心，不是调用一个外部 Hermes 服务。每轮由后端启动隔离的 Hermes `AIAgent` 子进程，保留上游的 Provider 流式调用、工具循环、工具参数累积与 `clarify` 人在环能力。

当前固定上游版本为 `v2026.8.19`（commit `fcbd1076a93841fa88855acce810e342a5b78101`，MIT）。源码本地副本在 `vendor/hermes-agent/`，已 Git 忽略，不会提交或上传；镜像构建时复制到 `/opt/hermes`。适配边界、许可证与升级方式见 [Hermes 源码说明](HERMES_SOURCE.md)。验证与发布状态见[版本记录](../../log/versions.md)。

## 当前能力

- 在 InsightPro Sidebar 或右下角打开统一对话工作区。
- 使用 InsightPro Supabase 身份；前端经受认证的流式 API 与 Agent 交互，不提供第二套用户密码。
- 从洞察页点击“Agent 分析”会创建 Context Session，并自动发送首条分析请求。
- 每位用户自动进入以稳定 `user_id` 标识的独立 Workspace；界面可显示姓名或邮箱，文件和 Session 不以邮箱作为主键。
- 普通用户可读写自己的 Workspace、只读公共知识库；管理员可进入并维护全部 AI 空间及公共知识库。
- Admin 可查看 Runtime、Workspace、最近使用时间、磁盘占用与基础用量；成员管理、禁用和恢复均以 InsightPro 的 `user_id` 为准。
- 生成解释、方案、代码草稿和 Patch；修改不会直接进入生产仓库。

支持 Backend 生成的 Context Bridge：GitHub Project、Cloud Solution、Vendor Update、Requirement、Solution 以受限 Session Snapshot 注入用户 Workspace；SAC Skill、匹配的 workflow 和最小 phase/gate 状态同时绑定。Agent 不连接数据库、不持有业务 API 凭据。

Agent 可提出 Requirement/Solution Draft Action；用户必须在 InsightPro 中读取并确认，Backend 校验权限与 Schema 后才会创建 Draft。核心工具白名单只含上游 `clarify` 和平台 `deliver_file`，没有通用 Terminal、Shell、Git 或部署权限；仍不支持生产源码/数据库直写。

模型调用统计只记录 Runtime 实际发出的请求；Input/Output Token 仅在 Provider 响应提供 `usage` 时记录，不估算、不补造。

## 运维

Insight-Agent 随主后端镜像部署；后端 Dockerfile 从固定的 Hermes 官方镜像取得运行环境，并把固定版本的本地上游源码复制至 `/opt/hermes`。遗留 `deploy/hermes/` Runtime 只保留给既有 Workspace 管理，不承接站内对话。

```bash
docker compose up -d --build backend frontend
docker compose ps
docker compose logs -f backend
```

InsightPro 主入口为 `/workbench/ai`；旧地址 `/insight-agent` 自动跳转到该入口。调试时依次检查 Supabase Session、`/api/agent/chat/stream` SSE 事件和后端日志；升级前阅读 [Hermes 源码说明](HERMES_SOURCE.md)。
