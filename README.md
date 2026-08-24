# InsightPro 商业洞察平台

InsightPro 是面向云服务商业市场的 AI 商业情报工作台。它把行业动态、技术趋势、政策、友商、招投标和客户需求集中采集，通过 AI 生成结构化判断，并以看板、历史日报和邮件简报交付给业务团队。

## 快速开始

### Docker Compose

前置条件：Docker、`docker-compose`，以及已配置的根目录 `.env`。

```bash
git clone https://github.com/Justin-TangPan/Insightpro.git
cd Insightpro

# 按下方“环境变量”创建 .env 后启动
docker-compose -p insight-web -f compose.yaml up --detach --build
./scripts/health-check.sh full
```

访问地址：

- Web：<http://localhost:3000>
- API：<http://localhost:8000>
- OpenAPI：<http://localhost:8000/docs>

已有生产服务器可使用带测试、构建、切换和回滚门禁的发布脚本：

```bash
sudo ./scripts/deploy-docker.sh
```

脚本依赖服务器已安装项目 Python 环境及 systemd unit；首次部署优先使用上面的 Compose 命令。旧 Docker Engine 18.09 环境需设置 `DOCKER_API_VERSION=1.39`，详见 [`doc/运维手册.md`](doc/运维手册.md)。

### 本地开发

需要 Python 3.11+ 和 Node.js 22+。

```bash
# 终端 1：后端
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

```bash
# 终端 2：前端
cd frontend
npm ci
npm run dev
```

开发时前端默认通过同源 `/api` 转发到 `http://127.0.0.1:8000`；需要直连其他后端时设置 `NEXT_PUBLIC_API_URL`。

## 环境变量

根目录 `.env` 至少应提供数据库和认证配置；AI 与邮件能力按需启用。

```env
# Supabase / PostgreSQL
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
DATABASE_URL=postgresql://user:password@host:6543/postgres
DIRECT_URL=postgresql://user:password@host:5432/postgres

# OpenAI 兼容 AI 接口
CHAT_API_URL=https://your-provider.example/v1/chat/completions
CHAT_API_KEY=your-api-key
CHAT_MODEL=your-model

# 应用地址与跨域
BASE_URL=http://localhost:3000
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
STARTUP_CATCHUP_ENABLED=true

# 邮件，可选
SMTP_HOST=smtp.qq.com
SMTP_PORT=465
SMTP_USER=sender@example.com
SMTP_PASSWORD=your-smtp-authorization-code
EMAIL_FROM=sender@example.com
EMAIL_TO=recipient@example.com

# DeepSearcher 网页读取，可选
JINA_API_TOKEN=your-jina-token
```

不要提交 `.env`、服务端密钥或数据库口令。

## 页面

| 页面 | 路径 | 说明 |
|---|---|---|
| 今日洞察 | `/` | 汇总热点、行业、政策、商机与系统状态 |
| 技术热点 | `/insights/hotspots` | GitHub 日/周/月榜、历史记录、AI 价值评估与项目速读 |
| 解决方案洞察 | `/insights/solutions` | 阿里云技术解决方案全量目录、简要分析与更新置顶 |
| 行业洞察 / 案例库 | `/insights/industry`、`/insights/industry/cases` | 行业动态、竞争格局和案例分析 |
| 新闻 / 政策 | `/insights/news`、`/insights/policy` | 商业快讯与政策影响 |
| 友商 / 商机 | `/insights/competitors`、`/insights/opportunities` | 云厂商动态、机会判断和行动建议 |
| 需求 / 招投标 | `/insights/demand`、`/insights/bidding` | 客户需求信号和招投标情报 |
| 数据大屏 | `/dashboard` | 运营指标和趋势图表 |
| 深度研报 | `/reports` | AI 分析任务与报告归档 |
| 搜索 / 历史日报 | `/search`、`/history` | 跨模块检索和历史数据回看 |
| 系统设置 | `/settings` | 服务状态、邮件订阅、邮件预览和管理操作 |
| 登录 / 注册 | `/auth/login`、`/auth/register` | Supabase 用户认证 |

## 常用 API

所有业务接口以 `/api` 为前缀。完整契约以 `/docs` 和 `backend/routers/` 为准。

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/system/health/live` | 进程存活探针 |
| GET | `/api/system/health/ready` | 数据库、数据新鲜度和热点数据就绪检查 |
| GET | `/api/data/freshness` | 核心数据集新鲜度 |
| GET | `/api/github-trending` | GitHub Trending 实时数据 |
| GET | `/api/github-trending/history` | GitHub Trending 历史数据 |
| GET | `/api/github-trending/business-eval` | 技术业务价值评估 |
| GET | `/api/solutions/aliyun` | 阿里云解决方案及更新状态 |
| POST | `/api/solutions/aliyun/refresh` | 登录用户手动检查解决方案更新 |
| GET | `/api/daily-insight` | 今日洞察聚合 |
| GET | `/api/search` | 跨模块搜索 |
| POST | `/api/chat` | 智能助手对话 |
| POST | `/api/tasks/analyze` | 创建 AI 分析任务 |
| GET | `/api/email/subscribers` | 管理员查看订阅者及其投递计划 |
| POST | `/api/email/subscribe` | 管理员添加订阅者并配置星期、时间 |
| PUT | `/api/email/subscribers/{id}` | 管理员更新单个订阅者的投递计划 |
| POST | `/api/email/subscribers/{id}/send` | 管理员向单个订阅者立即发送 |
| GET | `/api/email/preview` | 管理员邮件预览 |
| POST | `/api/email/send-now` | 管理员立即发送日报 |

## 项目结构

```text
insight-web/
├── backend/             # FastAPI、采集器、业务服务和测试
├── frontend/            # Next.js 应用、Prisma schema 和静态资源
├── scripts/             # 部署、健康检查和故障恢复脚本
├── deploy/systemd/      # 生产守护 unit
├── doc/                 # 产品、技术、数据库和运维文档
├── log/versions.md      # 内部迭代与正式发布记录
└── compose.yaml         # 生产容器编排
```

## 验证与运维

`v0.3.0` 发布前已通过 28 项后端测试、前端 ESLint 与生产构建、Docker 双容器健康检查及端到端数据检查。

```bash
# 后端
cd backend && STARTUP_CATCHUP_ENABLED=false python -m pytest -q

# 前端
cd frontend && npm run lint && npm run build

# 已启动环境的端到端检查
./scripts/health-check.sh full
```

## 能力概览

| 领域 | 能力 |
|---|---|
| 情报采集 | GitHub Trending、阿里云解决方案、百度热搜、行业新闻、政策、云厂商动态、招投标和需求信号 |
| AI 分析 | 技术业务价值评估、项目用途总结、行业判断、商机建议和深度研报 |
| 业务交付 | 首页看板、专题页面、全局搜索、历史日报、智能助手和邮件简报 |
| 权限管理 | Supabase Auth；订阅者、测试邮件、立即发送和分析数据仅管理员可操作 |
| 数据可靠性 | PostgreSQL 持久化、启动补跑、数据新鲜度检测、运行时 schema 校准 |
| 生产运维 | Docker Compose、非 root 容器、同源 API 代理、healthcheck 和 systemd 守护 |

## 架构

```text
浏览器
  └─ Next.js 16 / React 19 :3000
       ├─ 页面、认证、图表、全局助手
       └─ /api/* 同源代理
            └─ FastAPI :8000
                 ├─ routers/  API 与权限边界
                 ├─ services/ 业务、AI、邮件与健康检查
                 ├─ crawlers.py / APScheduler 采集与定时任务
                 └─ Supabase PostgreSQL + 可选 DeepSearcher/Qdrant
```

| 层 | 技术 |
|---|---|
| 前端 | Next.js 16、React 19、TypeScript、Tailwind CSS 4、Recharts、Prisma 7 |
| 后端 | Python 3.11、FastAPI、Uvicorn、Pydantic 2、APScheduler、httpx |
| AI | OpenAI 兼容聊天接口；DeepSearcher / Qdrant 为可选增强 |
| 数据 | Supabase PostgreSQL；SQLite 仅保留历史迁移工具 |
| 部署 | Docker Compose、Node.js 22、systemd、Docker healthcheck |


## v0.3.0 重点更新

- 技术热点从 GitHub Trending 采集扩展到 AI 业务价值评估和项目用途速读，覆盖最多 25 个项目。
- 新增解决方案洞察，每天 09:00 检查阿里云技术解决方案，生成 20–30 字简介并将变化内容置顶。
- 新增 Supabase Auth 登录、注册和管理员权限边界，并修复已连接环境被误报为“未连接”的状态展示。
- 邮件订阅支持按订阅者配置星期与时间、单人立即发送，预览与正式发送复用同一模板。
- 新增数据新鲜度、存活/就绪探针、启动补跑和 Docker 健康守护。
- 前端升级到 Next.js 16 / React 19，后端拆分为 FastAPI 路由与服务模块。
- 生产数据统一使用 Supabase PostgreSQL，Prisma schema 与运行时结构校准保持一致。


| 操作 | 命令 |
|---|---|
| 查看容器 | `docker-compose -p insight-web -f compose.yaml ps` |
| 跟踪日志 | `docker-compose -p insight-web -f compose.yaml logs --tail 100 -f` |
| 重启服务 | `docker-compose -p insight-web -f compose.yaml restart` |
| 重新构建 | `docker-compose -p insight-web -f compose.yaml up --detach --build` |
| 守护日志 | `journalctl -u insight-docker-health-guard.service -n 50 --no-pager` |

## 文档与版本

- [`log/versions.md`](log/versions.md)：完整内部迭代和发布记录。
- [`doc/运维手册.md`](doc/运维手册.md)：生产部署、开机恢复、巡检与补跑。
- [`doc/database-schema.md`](doc/database-schema.md)：数据库结构。
- [`doc/InsightPro-技术与商业报告.md`](doc/InsightPro-技术与商业报告.md)：技术与商业能力说明。

