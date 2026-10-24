# InsightPro

> AI 驱动的技术解决方案洞察与决策工作台 · `v1.0.0-rc.42`

[![Version](https://img.shields.io/badge/version-1.0.0--rc.42-176b46)](https://github.com/Justin-TangPan/Insightpro)
[![Next.js](https://img.shields.io/badge/Next.js-16-000000?logo=nextdotjs)](frontend/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.128-009688?logo=fastapi)](backend/)
[![Supabase](https://img.shields.io/badge/Supabase-PostgreSQL-3FCF8E?logo=supabase&logoColor=white)](doc/database-schema.md)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)](compose.yaml)

InsightPro 面向解决方案架构师、技术负责人和技术决策团队：在首页汇总 AI 情报，跟踪 GitHub 项目、厂商 AI 应用与官方解决方案，将洞察沉淀为可复用的方案实践，并在统一账号体系下提供隔离的团队 AI Space。

## 核心价值

- **持续洞察**：从首页雷达查看近期信号，跟踪 GitHub 热门项目、厂商 AI 应用和官方解决方案目录变化。
- **辅助判断**：通过 AI 生成项目速读、技术价值评估和分析报告，帮助团队快速识别值得投入的方向。
- **推动落地**：将洞察保存为方案实践，并在 AI 工作区中基于背景材料开展分析和交付。

```text
首页情报雷达 → GitHub / AI 应用 / 解决方案 → 方案实践 → AI 工作区
```

当前候选版本为 `v1.0.0-rc.42`；完成国内舆情数据接入验收后再标记正式 `v1.0.0`。详情见[版本记录](log/versions.md)；InsightPro 仍是唯一账号、业务系统和写入边界。

## 产品预览

以下截图来自 `v1.0.0-rc.16` 的实际运行页面；情报数量和内容会随采集更新。

### 首页 · AI 情报雷达

![InsightPro 首页 AI 情报雷达](doc/assets/readme/home.png)

### AI 应用

![InsightPro AI 应用发布与分析](doc/assets/readme/ai-apps.png)

### GitHub 项目趋势

![InsightPro GitHub 项目趋势](doc/assets/readme/hotspots.png)

### 解决方案

![InsightPro 官方解决方案目录与变化](doc/assets/readme/solutions.png)

## 核心能力

### 首页 · AI 情报雷达

按 AI 应用、Agent、模型与技术、AI Infra、商业化五个方向呈现近 7 天情报，点击雷达编号可查看对应信号。

### GitHub

跟踪 GitHub Trending 日榜、周榜和月榜，提供历史变化、项目用途速读和技术价值评估。热点项目可以一键保存为方案实践。

### AI 应用

汇集各大厂商官方 AI 应用发布信息，保留官方原文链接，并展示应用能力、生态机会和待验证点。

### 解决方案

同步阿里云、华为云官方技术解决方案目录，每日识别新增、更新和下线变化，并保留原始来源。

### 方案实践

集中管理团队的方案实践，支持背景信息、状态、分类、版本和参考链接，并可进入 AI 工作区继续分析。历史 Requirement 材料保留兼容关联，旧需求列表入口跳转到方案实践。用户数据按账号隔离。

### Insight-Agent

InsightPro 内置的 AI 智能工作区，直接复用 [Nous Research Hermes Agent](https://github.com/NousResearch/hermes-agent) 的源码核心。每轮由 Hermes `AIAgent` 执行模型流式调用、工具循环、工具参数累积和 `clarify` 人在环决策；InsightPro 负责身份、业务 Context、知识库、可下载交付件和业务写入确认。GitHub Project、Cloud Solution、Requirement 与 Solution 可以直接“使用 Agent 分析”；Backend 只向核心传入已授权的对象快照，前端不持有数据库或模型密钥。

当前固定 Hermes 版本为 `v2026.8.19`（commit `fcbd1076a93841fa88855acce810e342a5b78101`），按 MIT License 使用。上游源码本地放在 `vendor/hermes-agent/`，被 Git 忽略，不会提交或上传；构建将其置于后端镜像的 `/opt/hermes`。适配边界、许可证和升级方式见 [Hermes 源码说明](services/insight-agent/HERMES_SOURCE.md)。

## 快速启动

### 1. 准备环境

- Docker Engine 24+
- Docker Compose
- Supabase PostgreSQL 与 Supabase Auth 项目

### 2. 获取项目

```bash
git clone https://github.com/Justin-TangPan/Insightpro.git
cd Insightpro
```

### 3. 配置环境变量

在项目根目录创建 `.env`：

```dotenv
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
DATABASE_URL=postgresql://user:password@host:6543/postgres
DIRECT_URL=postgresql://user:password@host:5432/postgres

BASE_URL=http://localhost:3000
HERMES_PUBLIC_URL=
AGENT_RUNTIME_CONTROL_URL=
CORS_ORIGINS=
STARTUP_CATCHUP_ENABLED=true
```

AI 分析、邮件订阅和 Insight-Agent 的配置方式见 [运维手册](doc/运维手册.md)。请勿提交 `.env` 或任何生产密钥。

### 4. 启动服务

```bash
docker-compose --project-name insight-web --file compose.yaml up --detach --build
bash scripts/health-check.sh full
```

### 5. 访问

- Web：<http://localhost:3000>
- API：<http://localhost:8000>
- OpenAPI：<http://localhost:8000/docs>

生产环境可使用带测试、健康检查和故障恢复的部署脚本：

```bash
sudo bash scripts/deploy-docker.sh
sudo bash deploy/hermes/manage.sh upgrade
```

主系统与 Insight-Agent 使用独立 Docker Compose project：主系统部署不会重建或中断 AI Space。详细配置见 [Insight-Agent 部署文档](services/insight-agent/DEPLOYMENT.md)。

## 技术栈

Next.js · React · TypeScript · FastAPI · Supabase PostgreSQL · Supabase Auth · Docker · APScheduler

## 文档

- [技术架构与业务架构](doc/技术架构与业务架构清单.md)
- [数据库设计](doc/database-schema.md)
- [部署与运维](doc/运维手册.md)
- [Insight-Agent](services/insight-agent/README.md)
- [版本记录](log/versions.md)
架构图：[`TECHNICAL_ARCHITECTURE.svg`](./TECHNICAL_ARCHITECTURE.svg)
