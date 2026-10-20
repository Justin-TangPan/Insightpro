# InsightAgent 源码核心

InsightAgent 直接导入 Nous Research Hermes 的 `run_agent.AIAgent`，执行原始
`agent.conversation_loop`、Provider streaming、`agent.tool_executor` 和 `clarify_tool`。
没有复制改写 Agent Loop，也不通过 Hermes CLI、Dashboard、Gateway 或 Runtime Manager 执行聊天。

源码版本固定为 `v2026.8.19`（commit `fcbd1076a93841fa88855acce810e342a5b78101`），本地副本来自
`NousResearch/hermes-agent`，并与基础镜像 `nousresearch/hermes-agent:v2026.8.19`
`sha256:3811ed13da874fba2ac99b6d492db9a203d34cb6dccf90d886948c00d0ccec09` 对齐。
构建时将本地副本复制至 `/opt/hermes`，并复用该镜像的独立虚拟环境。
保留 `/opt/hermes/LICENSE`（MIT，Copyright (c) 2025 Nous Research）及原始版权声明。
升级只变更固定版本并重新运行源码核心集成测试；上游核心当前零修改。

平台适配代码：`backend/services/hermes_core_worker.py` 与 `embedded_agent_service.py`。
每轮使用独立本地 Python 子进程，stdin 传入授权后的上下文与决策，stdout 输出实时事件。
业务历史保存在 `agent_sessions.runtime_history`，保留原始 tool_call/tool_result 关系。
只向核心开放 `clarify` 和平台 `deliver_file` 工具；后者生成可下载文本，不执行部署。
平台知识库检索、权限、业务草稿确认、交付件保存沿用现有服务。

当前运行约束：单 API worker，最多六个并发轮次；停止/断开连接终止对应本地进程。
人在环等待最长三十分钟（整轮总时限），超时不替用户批准。重启后不能恢复未结束轮次。
旧 Hermes 容器与管理接口保留用于已有工作空间管理，不承接新的交互执行。
