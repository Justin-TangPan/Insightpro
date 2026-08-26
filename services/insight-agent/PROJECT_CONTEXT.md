# InsightPro Project Context

InsightPro 是技术解决方案洞察平台，核心闭环为 Insight → Requirement → Solution。

主要模块：首页技术方案简报、技术热点、阿里云解决方案洞察、厂商动态、全局搜索、用户自有 Solutions 与 Requirements、后台 AI 摘要/评估/研报/采集加工、Scheduler 和 Health Check。

技术栈：Next.js、FastAPI、Supabase PostgreSQL/Auth、Docker Compose、systemd。Workbench 遵循 Router → Service → Repository → Database，现有稳定代码不为形式统一而重构。

`aliyun_solutions` 是外部厂商洞察数据；`solutions` 是按 `user_id` 隔离的用户自有方案；Requirements 可以从洞察创建并关联自有 Solution。

产品不包含行业洞察、政策雷达和招标信息。Insight-Agent 当前只读，不执行代码、写业务数据、提交 Git 或部署。
