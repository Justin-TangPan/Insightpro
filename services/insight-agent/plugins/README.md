# Insight-Agent Plugins

插件是随 Insight-Agent 发布的只读知识包。每个插件目录包含：

- `manifest.json`：`id`、版本、启用开关及知识入口；
- `AGENT.md`：面向 Agent 的稳定规则、工作流和安全边界。

Backend 每次生成回复时发现已启用插件；Hermes Runtime 启动时把插件同步到 `/knowledge/public/plugins/`。修改插件后重新构建并升级 Insight-Agent；不需要修改业务代码或重建用户 Workspace。

插件不能直接写入 InsightPro 数据、跳过人工确认，或将云端静态检查描述为部署成功。
