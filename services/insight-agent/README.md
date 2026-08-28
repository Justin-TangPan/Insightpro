# Insight-Agent

Insight-Agent 是 InsightPro 内置的 AI 智能工作区，底层运行固定版本 Hermes Agent 原生 Dashboard 和 Agent 能力，不使用宿主机 Hermes，也不修改 Hermes Agent Core。

## 当前能力

- 在 InsightPro Sidebar 中打开完整工作区。
- 在普通页面使用可拖动、缩放、最小化和最大化的浮窗。
- 浮窗和完整工作区复用同一个浏览器 iframe 与 Hermes Session。
- 使用 InsightPro Supabase 身份单点进入，不提供第二套用户密码。
- 每位用户自动进入以稳定 `user_id` 标识的独立 Workspace；界面可显示姓名或邮箱，文件和 Session 不以邮箱作为主键。
- 普通用户可读写自己的 Workspace、只读公共知识库；管理员可进入并维护全部 AI 空间及公共知识库。
- Admin 可查看 Runtime、Workspace、最近使用时间、磁盘占用与基础用量；成员管理、禁用和恢复均以 InsightPro 的 `user_id` 为准。
- 生成解释、方案、代码草稿和 Patch；修改不会直接进入生产仓库。

当前不支持生产源码/数据库写入、业务对象写入、Shell/Git 操作、部署、Context Bridge，以及自动携带 Insight/Solution/Requirement 上下文。

模型调用统计只记录 Runtime 实际发出的请求；Input/Output Token 仅在 Provider 响应提供 `usage` 时记录，不估算、不补造。

## 运维

底层部署位于 `deploy/hermes/`，使用官方 Hermes Agent 容器镜像构建独立 Runtime。

```bash
sudo ./deploy/hermes/manage.sh start
sudo ./deploy/hermes/manage.sh health
sudo ./deploy/hermes/manage.sh status
sudo ./deploy/hermes/manage.sh logs
sudo ./deploy/hermes/manage.sh stop
sudo ./deploy/hermes/manage.sh upgrade
```

InsightPro 入口为 `/insight-agent`。调试时依次检查 Supabase Session、SSO Ticket、Gateway `/healthz` 和 Hermes 容器健康状态。升级前阅读 [DEPLOYMENT.md](./DEPLOYMENT.md)。
