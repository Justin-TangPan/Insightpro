# Insight-Agent

Insight-Agent 是 InsightPro 内置的只读 AI 智能工作区。产品界面统一使用 Insight-Agent 名称；底层复用固定版本 OpenCode 原生 Web、Session 和 Agent 能力，不修改 OpenCode Core。

## 当前能力

- 在 InsightPro Sidebar 中打开完整工作区。
- 在普通页面使用可拖动、缩放、最小化和最大化的浮窗。
- 浮窗和完整工作区复用同一个浏览器 iframe 与 OpenCode Session。
- 使用 InsightPro Supabase 身份单点进入，不提供第二套用户密码。
- 阅读和检索 InsightPro 的源码、数据模型、API、测试、部署与文档。
- 生成解释、方案、代码草稿和 Patch 建议。

当前不支持源码/数据库写入、业务对象写入、Git 操作、部署、Context Bridge、自动携带 Insight/Solution/Requirement 上下文及安全的多用户共享实例。

## 运维

底层部署实现暂位于 `deploy/opencode/`，这是 Insight-Agent 对固定 OpenCode Runtime 的内部适配层，不是产品入口。

```bash
sudo ./deploy/opencode/manage.sh start
sudo ./deploy/opencode/manage.sh health
sudo ./deploy/opencode/manage.sh status
sudo ./deploy/opencode/manage.sh logs
sudo ./deploy/opencode/manage.sh stop
sudo ./deploy/opencode/manage.sh upgrade
```

InsightPro 入口为 `/insight-agent`。调试时依次检查 Supabase Session、`POST /api/auth/opencode/ticket`、Gateway `/healthz` 和容器 `/global/health`。升级前阅读 [DEPLOYMENT.md](./DEPLOYMENT.md)，故障判断参见 [SECURITY.md](./SECURITY.md) 和 [ARCHITECTURE.md](./ARCHITECTURE.md)。
