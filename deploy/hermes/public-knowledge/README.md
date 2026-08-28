# InsightPro 公共知识库

这里存放所有 Insight-Agent 用户共享的公共资料。

- 普通用户：只读。
- InsightPro Admin：可在自己的 Insight-Agent 空间中维护。
- `insight-public-data.json`：Runtime Manager 每五分钟从 InsightPro 公共 API 刷新，包含首页模块、技术热点和解决方案洞察；所有用户只读。回答“最近”“当前”“今日”“新增”的平台数据问题时，应先读取此文件，并以其中的 `refreshedAt` 为数据时间。

不得在此保存 `.env`、Token、密码、生产密钥或其他敏感信息。
