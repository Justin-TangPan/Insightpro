# Insight-Agent Architecture

```text
Browser / InsightPro shell
  └─ Insight-Agent UI
       └─ InsightPro Agent API
            └─ local Hermes `AIAgent` source process
                 ├─ Provider streaming + tool loop
                 ├─ clarify 人在环决策
                 └─ `deliver_file` 交付件工具
```

对象页打开 Insight-Agent 时，浏览器先向 InsightPro API 创建 `agent_session`。Backend 按 `user_id` 读取并过滤业务对象，保存小型 `context_snapshot`。每轮后端启动一个本地 Hermes `AIAgent` 进程，向它传入该快照、对话历史和允许的工具；Hermes 从不访问业务数据库。

Agent 若要形成业务资产，只能写 `.insight/INSIGHT_ACTION.json` 的白名单 Draft。用户在 InsightPro Shell 读取并确认后，Backend 校验 Action Schema、对象所有权和关联 Requirement，最后复用 Workbench Service 写入 Draft。

源码核心固定为 Hermes `v2026.8.19`（commit `fcbd1076a93841fa88855acce810e342a5b78101`，MIT）。本地源副本位于 `vendor/hermes-agent/`，Git 忽略；Docker 构建复制它到 `/opt/hermes`。InsightPro 不修改上游 Agent Loop，只通过 `hermes_core_worker.py` 适配事件、受控工具、用户决策和交付件。

## 服务和网络

InsightPro 前后端由根 Compose 管理。Insight-Agent 核心位于后端镜像：每轮在临时目录启动独立本地 Python 进程，直接导入 `/opt/hermes/run_agent.py` 的 `AIAgent`。它不经过 Hermes CLI、Dashboard、Gateway、WebSocket 或 Runtime Manager。遗留的独立 Hermes Runtime 只服务已有 Workspace 管理，不承接站内对话。

## UI 和 Session

`InsightAgentShell` 在 Next.js 根布局内持久挂载。浮窗、Split 和完整页复用同一 InsightPro Session；交互式消息经 Backend Adapter 进入同一套 Hermes 核心。`agent_sessions.runtime_history` 持久保存 Hermes 返回的 tool-call/tool-result 历史，下一轮继续原始 Agent Loop 语义。

## 用户和认证

Supabase Auth 是唯一身份源。前端以 Supabase access token 调用同源 InsightPro API；FastAPI 验证后取得可信 `user_id`、身份角色和目标空间，并将已授权的 Context Snapshot 传给本地 Hermes 子进程。用户退出 InsightPro 时失去 API 会话。只有管理员可访问其他用户空间的管理接口。

## 数据与安全边界

- 每轮 Hermes 进程仅获得临时 `HERMES_HOME`，无生产 `.env`、Docker Socket、业务 API 或数据库凭据。
- 工具白名单只含上游 `clarify` 和平台 `deliver_file`；后者只返回校验后的文本交付件，不写工作区、不部署。
- 业务写入仍是 InsightPro 的结构化 Draft 提案，必须由用户确认后写入。
- Provider key 只经子进程 stdin 传递，不写入磁盘或前端。

Hermes 子进程运行在后端容器内的临时目录；容器未挂载生产目录或 Docker Socket。现阶段隔离边界是进程、临时 `HERMES_HOME` 和受控工具白名单；若并发或多租户隔离要求提升，应改为独立 worker 容器或 sandbox。

## 运维可见性

FastAPI 记录 Provider 明确返回的 Token 和管理员业务操作；不记录聊天正文、文件内容或 Secret。人在环请求在后端内存保留至回答或最长 30 分钟；进程或服务重启会终止未完成轮次，客户端需要重新发起。

`agent_*` 表仍保存既有会话与审计数据。旧原生 Chat Runtime 与独立 Hermes Runtime 不在站内 Agent 主链路；主链路始终使用本地 Hermes 源码进程。
