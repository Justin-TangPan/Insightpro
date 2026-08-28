# InsightPro

> 技术解决方案洞察平台 · `v0.5.0`

[![Version](https://img.shields.io/badge/version-0.5.0-176b46)](https://github.com/Justin-TangPan/Insightpro)
[![Next.js](https://img.shields.io/badge/Next.js-16-000000?logo=nextdotjs)](frontend/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.128-009688?logo=fastapi)](backend/)
[![Supabase](https://img.shields.io/badge/Supabase-PostgreSQL-3FCF8E?logo=supabase&logoColor=white)](doc/database-schema.md)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)](compose.yaml)

InsightPro 面向解决方案架构师、技术负责人和技术决策团队：持续发现值得关注的技术项目与官方解决方案，将洞察沉淀为可跟踪的需求和可复用的方案，并在统一账号体系下提供隔离的团队 AI Space。

## 核心价值

- **持续洞察**：每日跟踪 GitHub 技术热点和官方技术解决方案目录变化，降低人工检索成本。
- **辅助判断**：通过 AI 生成项目速读、技术价值评估和分析报告，帮助团队快速识别值得投入的方向。
- **推动落地**：将洞察直接沉淀为 Requirement，并进一步创建或关联 Solution，形成从发现到执行的完整链路。

```text
Insight → Requirement → Solution
```

`v0.5.0` 将 Insight-Agent 纳入正式团队能力：成员拥有独立 Workspace 与 Session，Admin 可管理成员、AI Space、公共知识库和基础运行用量；InsightPro 仍是唯一账号与业务系统。

## 产品预览

### 技术热点追踪

![InsightPro 技术热点追踪](doc/assets/readme/hotspots.png)

### 解决方案洞察

![InsightPro 解决方案洞察](doc/assets/readme/solutions.png)

## 核心能力

### 技术热点

跟踪 GitHub Trending 日榜、周榜和月榜，提供历史变化、项目用途速读和技术价值评估。热点项目可以一键暂存为 Requirement。

### 解决方案洞察

同步官方技术解决方案一级、二级目录，每日识别新增、更新和下线变化，并保留原始来源。

### Workbench

集中管理团队自己的 Requirements 和 Solutions，支持状态、优先级、版本、来源以及双向关联。用户数据按账号隔离。

### Insight-Agent

InsightPro 内置的 AI 智能工作区。每位成员有独立 Workspace、Session 和 Runtime；公共知识库对成员只读、由 Admin 维护。成员可在自己的空间内创建、修改和删除文件，但不具备生产目录、数据库、密钥、Docker 或部署权限。

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
CORS_ORIGINS=http://localhost:3000
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
