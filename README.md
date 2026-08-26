# InsightPro 技术解决方案洞察平台

InsightPro v0.4.0 面向解决方案架构师和技术决策团队，持续跟踪开源技术项目、云厂商解决方案与产品变化，并通过 Workbench 将洞察转化为可管理的 Requirement 和 Solution。

## 当前能力

| 能力域 | 内容 |
|---|---|
| 技术热点 | GitHub Trending 日/周/月榜、历史记录、项目用途速读和业务价值评估 |
| 解决方案 | 复刻阿里云官方一级/二级目录、每日差异识别、新增置顶、20–30 字价值摘要 |
| 友商动态 | AWS、Azure、阿里云、腾讯云、火山云的产品动态与能力对照 |
| 工作台 | `Insight → Requirement → Solution`，支持需求、方案及关联关系管理 |
| 分析交付 | 首页洞察、跨五类对象的相关性搜索、Insight-Agent 只读智能工作区、深度研报和邮件简报 |
| 平台治理 | Supabase Auth、分级权限、数据新鲜度、启动补跑、健康检查和访问分析 |

业务范围仅限技术项目、技术解决方案及云产品能力信息。详细边界、业务流程和技术组件见 [技术架构与业务架构清单](doc/技术架构与业务架构清单.md)。

## 快速开始

前置条件：Docker、`docker-compose`，以及按下方说明配置的根目录 `.env`。

```bash
git clone https://github.com/Justin-TangPan/Insightpro.git
cd Insightpro
docker-compose -p insight-web -f compose.yaml up --detach --build
./scripts/health-check.sh full
```

访问地址：

- Web：<http://localhost:3000>
- API：<http://localhost:8000>
- OpenAPI：<http://localhost:8000/docs>
- Insight-Agent：站内入口 `/insight-agent`；底层 Runtime 由独立 Compose project 提供并复用 InsightPro Supabase 身份。

生产服务器使用带测试、构建、切换和回滚门禁的发布脚本：

```bash
sudo ./scripts/deploy-docker.sh
```

生产服务器当前使用 Docker Engine 28.5.2；安装与回滚说明见 [运维手册](doc/运维手册.md)。

## 本地开发

需要 Python 3.11+ 和 Node.js 22+。

```bash
# 后端
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

```bash
# 前端（另一个终端）
cd frontend
npm ci
npm run dev
```

前端将同源 `/api/*` 转发到 `API_PROXY_TARGET`；本地默认值为 `http://127.0.0.1:8000`。

## 环境变量

数据库与认证为必需能力；AI 和邮件按需启用。不要提交 `.env`、服务端密钥或数据库口令。

```dotenv
# Supabase / PostgreSQL
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
DATABASE_URL=postgresql://user:password@host:6543/postgres
DIRECT_URL=postgresql://user:password@host:5432/postgres

# OpenAI 兼容接口
CHAT_API_URL=https://your-provider.example/v1/chat/completions
CHAT_API_KEY=your-api-key
CHAT_MODEL=your-model

# 应用
BASE_URL=http://localhost:3000
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
STARTUP_CATCHUP_ENABLED=true
NEXT_PUBLIC_OPENCODE_URL=http://your-server:4096

# SMTP（可选）
SMTP_HOST=smtp.qq.com
SMTP_PORT=465
SMTP_USER=sender@example.com
SMTP_PASSWORD=your-smtp-authorization-code
EMAIL_FROM=sender@example.com
EMAIL_TO=recipient@example.com
```

## 页面入口

| 路径 | 用途 | 访问要求 |
|---|---|---|
| `/` | 今日技术热点、方案变化和友商动态 | 公开 |
| `/insights/hotspots` | 技术热点与 AI 价值评估 | 公开；刷新需登录 |
| `/insights/solutions` | 解决方案目录与变化记录 | 公开；刷新需登录 |
| `/insights/competitors` | 云厂商产品动态与能力对照 | 公开；刷新需登录 |
| `/workbench/requirements` | Requirement 列表、筛选、详情与方案关联 | 登录 |
| `/workbench/solutions` | 自有 Solution 列表、详情与相关需求 | 登录 |
| `/insight-agent` | Insight-Agent 完整只读工作区 | 登录；当前仅指定管理员 |
| `/dashboard` | 核心数据和服务状态 | 公开 |
| `/search`、`/history` | 跨域检索与历史回看；登录后搜索个人 Workbench | 公开/可选登录 |
| `/reports` | AI 分析任务与报告归档 | 登录 |
| `/settings` | 账号、服务状态和邮件管理 | 登录；邮件管理需管理员 |
| `/auth/login`、`/auth/register` | Supabase 用户认证 | 公开 |

侧边栏和右下角浮窗共用同一个 Insight-Agent iframe 与 Session。Gateway 使用一次性 ticket 复用 InsightPro 身份，不让 Agent 访问业务数据库；当前单实例仅授权指定管理员，不能作为多用户隔离方案。

完整 API 与权限矩阵见 [技术架构与业务架构清单](doc/技术架构与业务架构清单.md)，运行时契约以 FastAPI `/docs` 为准。

## 项目结构

```text
insight-web/
├── backend/             # FastAPI、Router/Service/Repository、采集器和测试
├── frontend/            # Next.js 应用、Prisma 数据契约和静态资源
├── scripts/             # 发布、健康检查和故障恢复
├── deploy/systemd/      # Compose 守护及历史回退 unit
├── deploy/opencode/     # 独立 OpenCode 镜像、Compose、配置与管理脚本
├── services/insight-agent/ # Insight-Agent 子项目文档与安全边界
├── doc/                 # 架构、数据库、运维和改进清单
├── log/                 # 版本与已关闭问题记录
└── compose.yaml         # 前后端生产编排
```

Insight-Agent Runtime 使用独立启动链路，不加入根目录 `compose.yaml`：

```bash
sudo ./deploy/opencode/manage.sh start
sudo ./deploy/opencode/manage.sh health
sudo ./deploy/opencode/manage.sh stop
sudo ./deploy/opencode/manage.sh upgrade
```

运行凭据位于 `/etc/insight-opencode/opencode.env`，持久化数据和只读隔离 Workspace 位于 `/var/lib/insight-opencode/`。二者均不得提交到 Git。完整说明见 [Insight-Agent README](services/insight-agent/README.md)。

## 验证

```bash
cd backend && STARTUP_CATCHUP_ENABLED=false python -m pytest -q
cd ../frontend && npm run lint && npx prisma validate && npm run build
cd .. && ./scripts/health-check.sh full
```

截至 2026-08-25，后端 33 项测试、前端 ESLint、Prisma 校验及 Next.js 18 路由生产构建均通过；部署状态以健康检查结果为准。

## 文档索引

- [技术架构与业务架构清单](doc/技术架构与业务架构清单.md)：产品边界、业务能力、系统组件、数据流、API、权限和风险。
- [数据库契约](doc/database-schema.md)：15 张 public 业务表及约束。
- [运维手册](doc/运维手册.md)：部署、发布、巡检、补跑和故障恢复。
- [改进清单](doc/整改方案.md)：当前仍需处理的技术债及触发条件。
- [版本日志](log/versions.md)：完整演进记录。
- [Insight-Agent](services/insight-agent/README.md)：内置 Agent 的架构、安全和部署入口。
