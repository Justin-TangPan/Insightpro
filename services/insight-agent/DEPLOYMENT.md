# Insight-Agent Deployment

## 组成

- `deploy/hermes/Dockerfile`：固定官方 Hermes Agent 镜像和 Runtime Manager。
- `deploy/hermes/compose.yaml`：独立 Compose、资源限制、隔离 Workspace 和健康检查。
- `deploy/hermes/nginx.conf.template`：SSO Gateway 与 iframe 来源限制。
- `deploy/hermes/manage.sh`：bootstrap/start/stop/upgrade/health/logs。
- `deploy/hermes/runtime-manager.mjs`：按 `user_id` 配置、启动和代理 Hermes Dashboard 子进程。

当前生产运行由独立 Docker Compose project 管理；不要把它加入 InsightPro 根 Compose，也不要让主系统的 `--remove-orphans` 操作接管它。

## 配置和持久化

运行配置位于 `/etc/insight-hermes/hermes.env`，权限应为 `0600`。Gateway Secret 主副本和后端只读副本位于同一目录。不要提交这些文件。

必要变量参见 `deploy/hermes/hermes.env.example`。嵌入部署必须将 `INSIGHT_APP_ORIGIN` 设置为准确的 InsightPro Origin。

持久化根目录默认 `/var/lib/insight-hermes`：

- `registry.json`：`user_id` 到内部 UID/端口的稳定映射；
- `spaces/<user_id>/`：该用户的 Workspace、Session、配置和运行状态；
- `knowledge/public/`：普通用户只读、管理员可维护的公共知识库；
- `template/`：首次创建 Workspace 使用的无 Secret 项目模板。

`OPENCODE_MAX_ACTIVE` 和 `OPENCODE_IDLE_SECONDS` 控制同时运行的用户进程及闲置回收。回收只停止进程，不删除任何持久化数据。

## 发布与验证

```bash
sudo ./deploy/hermes/manage.sh upgrade
sudo ./deploy/hermes/manage.sh health
./scripts/health-check.sh full
```

验证匿名 Gateway 请求被拦截、普通用户 A/B 的 Session 和文件互不可见、公共知识库只读、管理员可进入目标用户空间并维护公共知识、生产目录和 Secret 未挂载、重启后 Session 仍存在。Insight-Agent 停止后，InsightPro full health 仍应通过。

升级失败时保持 InsightPro 不动，使用固定镜像版本回退并重新执行 `upgrade`。持久化目录不要随容器回滚删除；Hermes Agent Core 不做本地 Patch。
