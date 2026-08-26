# Insight-Agent Deployment

## 组成

- `deploy/opencode/Dockerfile`：固定 OpenCode 版本的非 root Runtime。
- `deploy/opencode/compose.yaml`：独立 Compose、资源限制、只读 Workspace 和健康检查。
- `deploy/opencode/nginx.conf.template`：SSO Gateway 与 iframe 来源限制。
- `deploy/opencode/manage.sh`：bootstrap/start/stop/upgrade/health/logs。
- `deploy/opencode/opencode.json`：模型与只读工具权限。

systemd unit 是 `insight-opencode.service`；内部名称暂保留以避免无收益的生产 unit 迁移，产品界面不暴露该名称。

## 配置和持久化

运行配置位于 `/etc/insight-opencode/opencode.env`，权限应为 `0600`。Gateway Secret 主副本和后端只读副本分别位于 `/etc/insight-opencode/gateway.secret` 与 `backend-gateway.secret`。不要提交这些文件。

必要变量参见 `deploy/opencode/opencode.env.example`。嵌入部署必须将 `INSIGHT_APP_ORIGIN` 设置为准确的 InsightPro Origin。生产域名启用 HTTPS 后，同时设置 `OPENCODE_COOKIE_SECURE=true`。

持久化根目录默认 `/var/lib/insight-opencode`：

- `data/`：Session 和消息；
- `state/`、`cache/`：Runtime 状态；
- `config/`：运行配置副本；
- `workspace/`：无 Secret 的独立 Git Workspace，在容器内只读。

## 发布与验证

```bash
sudo ./deploy/opencode/manage.sh upgrade
sudo ./deploy/opencode/manage.sh health
./scripts/health-check.sh full
```

验证匿名 Gateway 请求被拦截、合法 SSO 可进入、iframe 响应带正确 `frame-ancestors`、Workspace 写入失败、`.env` 不存在、OpenCode 重启后 Session 仍存在。Insight-Agent 停止后，InsightPro full health 仍应通过。

升级失败时保持 InsightPro 不动，使用固定镜像版本回退 `Dockerfile`/Compose 并重新执行 `upgrade`。持久化目录不要随容器回滚删除；回滚前先备份 data/state。OpenCode Core 不做本地 Patch。
