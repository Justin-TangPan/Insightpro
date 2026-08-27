# InsightPro

> 技术解决方案洞察平台 · 当前版本 `v0.4.0`

InsightPro 面向解决方案架构师、技术负责人和技术决策团队，持续跟踪高价值开源技术与官方技术解决方案，并将外部洞察沉淀为团队可管理的 Requirement 和 Solution。

平台当前核心闭环为：

```text
技术热点 / 官方解决方案
          ↓
      Requirement
          ↓
       Solution
```

InsightPro 不再提供行业洞察、政策雷达、招标信息和云厂商洞察。仓库中可能仍保留少量兼容路由或历史采集代码，它们不属于当前产品能力，也不应作为新增功能依赖。

## 1. 产品能力

### 技术热点

- 跟踪 GitHub Trending 日榜、周榜和月榜。
- 保存历史快照，展示语言、Stars、Forks 和增长数据。
- 通过后台 AI Pipeline 生成项目用途速读和技术价值评估。
- 支持将 GitHub 项目一键“暂存需求”：系统直接创建草稿 Requirement，并保留仓库名称、来源链接和项目描述。

### 解决方案洞察

- 复刻阿里云官方技术解决方案一级、二级领域目录。
- 每日与上一版目录对比，识别新增、内容更新和下线方案。
- 414 项历史存量作为普通基线；只有后续真实新增或变化的方案获得变化标记。
- 支持从官方方案进入 Requirement 创建页，并自动携带来源信息。

### Workbench

Workbench 管理 InsightPro 自有业务对象，不修改外部洞察数据。

| 对象 | 核心能力 |
|---|---|
| Requirement | 创建、编辑、删除、列表、详情、状态筛选、来源追踪、关联 Solution |
| Solution | 创建、编辑、删除、列表、详情、版本与参考链接、查看关联 Requirement |

Requirement 与 Solution 均按 Supabase `user_id` 隔离。用户只能读取和修改自己的 Workbench 数据。

### Insight-Agent

Insight-Agent 是 InsightPro 内置的交互式 AI 工作区，底层复用固定版本 OpenCode 原生 Web 和 Agent Runtime，但产品界面不暴露 OpenCode 名称。

- Sidebar 可进入完整工作区，普通页面可使用右下角浮窗。
- 浮窗、最大化工作区和还原状态复用同一 iframe 与 Session。
- 通过一次性 SSO ticket 复用 InsightPro 的 Supabase 身份，不向浏览器下发服务端密钥。
- 自动进入 InsightPro 专用 Workspace，无需用户选择项目。
- 可读取 InsightPro 项目副本和平台公开数据，也可在隔离 Workspace 中工作。
- 不直接写入生产仓库、生产数据库、Requirement、Solution 或生产配置。

当前 OpenCode 单实例不具备可靠的用户级 Session、Workspace 和 Provider 隔离，因此 Insight-Agent 仅允许 `OPENCODE_ALLOWED_EMAIL` 指定的单一管理员使用。增加多用户前必须采用用户独立实例或等效的强隔离方案，不能仅放宽 SSO 白名单。

### 平台能力

- Supabase 登录、注册、退出、Session 恢复和当前用户状态管理。
- `user` / `admin` 权限分级；用户列表、邮件管理、数据源配置和安全设置仅管理员可见且由后端校验。
- 绿色、极简黑白、橙色暖色、蓝色和紫色主题。
- 中英文界面偏好、紧凑度和动画开关，本地持久化。
- 技术解决方案邮件日报：官方方案总量、当日新增/更新、技术热点和技术价值评估。
- 定时采集、启动补跑、数据新鲜度检查、健康探针和部署健康守护。
- 深度研报、搜索和后台 AI 数据加工。

## 2. 系统架构

```text
Browser
  │
  ├── InsightPro Web :3000
  │     Next.js 16 / React 19
  │          │ same-origin /api proxy
  │          ▼
  │     InsightPro API :8000
  │     FastAPI / APScheduler
  │          │
  │          ├── Supabase Auth
  │          ├── Supabase PostgreSQL
  │          ├── GitHub / 阿里云官方目录
  │          ├── OpenAI-compatible AI API
  │          └── SMTP
  │
  └── Insight-Agent Gateway :4096
        SSO / iframe policy / access control
                  │
                  ▼
        OpenCode Runtime（独立 Compose project）
                  │
                  ▼
        独立 Session / Config / Workspace
```

主系统由根目录 `compose.yaml` 编排，包含：

- `insight-frontend`：Next.js Web，端口 `3000`。
- `insight-backend`：FastAPI API 和单实例定时调度器，端口 `8000`。
- `insight-network`：主系统内部 Docker 网络。

Insight-Agent 使用 `deploy/opencode/compose.yaml` 独立部署，不加入 `insight-web` Compose project。主系统发布、`--remove-orphans`、readiness 和健康守护不会停止 Insight-Agent；Insight-Agent 不可用也不会阻断 InsightPro 主业务。

Workbench 新代码遵循：

```text
Router → Service → Repository → PostgreSQL
```

现有稳定模块保持原结构，不为形式统一进行大规模重构。

## 3. 技术栈

| 层级 | 技术 |
|---|---|
| Web | Next.js 16、React 19、TypeScript、Tailwind CSS 4 |
| API | FastAPI、Pydantic、Uvicorn |
| 数据与认证 | Supabase PostgreSQL、Supabase Auth |
| 调度 | APScheduler，Asia/Shanghai 时区 |
| AI | OpenAI-compatible Chat Completions、Insight-Agent/OpenCode Runtime |
| 部署 | Docker、Docker Compose、systemd health guard |
| 测试 | Pytest、ESLint、TypeScript、Next.js production build |

## 4. 页面与权限

| 路径 | 用途 | 权限 |
|---|---|---|
| `/` | 首页技术方案简报和 Workbench 概览 | 公开；私有数据登录后显示 |
| `/insights/hotspots` | GitHub 技术热点、历史和价值评估 | 浏览公开；刷新和暂存需求需登录 |
| `/insights/solutions` | 阿里云官方解决方案目录和每日变化 | 浏览公开；刷新和创建需求需登录 |
| `/workbench/requirements` | Requirement 列表、筛选、详情和关联 | 登录，仅本人数据 |
| `/workbench/solutions` | 自有 Solution 列表、详情和关联 | 登录，仅本人数据 |
| `/insight-agent` | Insight-Agent 完整工作区 | 登录，当前限指定管理员 |
| `/search` | 公共洞察搜索及用户 Workbench 搜索 | 公共/登录增强 |
| `/reports` | AI 分析任务与报告归档 | 登录 |
| `/settings` | 账号、主题、语言和交互偏好 | 登录 |
| `/settings` 管理员板块 | 用户、订阅、数据源和安全设置 | 管理员 |
| `/auth/login`、`/auth/register` | 登录与注册 | 公开 |

管理员身份来自 Supabase `app_metadata.role = "admin"`。前端隐藏仅用于改善体验，真正权限边界由 FastAPI 的 `require_auth` 和 `require_admin` 强制执行。

## 5. 项目结构

```text
insight-web/
├── backend/
│   ├── routers/                 # FastAPI 路由与权限入口
│   ├── services/                # 业务逻辑、采集、邮件、SSO、健康检查
│   ├── repositories/            # Workbench 与 SSO 数据访问
│   ├── tests/                   # 后端自动化测试
│   ├── main.py                  # API、生命周期和定时任务注册
│   └── settings.py              # 服务端统一环境配置
├── frontend/
│   ├── src/app/                 # Next.js App Router 页面
│   ├── src/components/          # 布局、认证、Sidebar、Agent Shell
│   ├── src/lib/                 # API、Workbench、用户偏好等客户端能力
│   ├── prisma/                  # 数据契约参考
│   └── Dockerfile
├── services/insight-agent/      # Insight-Agent 产品、架构、安全和部署文档
├── deploy/
│   ├── opencode/                # 独立 Agent Runtime、Gateway 与管理脚本
│   └── systemd/                 # 主系统健康守护和历史回退单元
├── scripts/                     # 部署、健康检查和恢复脚本
├── doc/                         # 数据库、架构和运维专题文档
├── log/                         # 版本与历史问题记录
└── compose.yaml                 # InsightPro 主系统编排
```

## 6. 快速开始

### 前置条件

- Linux 服务器或开发机。
- Docker Engine 24+。
- 独立 `docker-compose` 命令；生产脚本当前使用该命令而不是 Compose v2 子命令。
- Supabase 项目及 PostgreSQL 连接信息。
- 可选：OpenAI-compatible 模型接口、SMTP、Insight-Agent Runtime。

若服务器缺少合适版本的 Docker/Compose，可运行：

```bash
sudo bash scripts/install-docker-compose.sh
```

### 配置

克隆项目并在仓库根目录创建 `.env`：

```bash
git clone https://github.com/Justin-TangPan/Insightpro.git
cd Insightpro
touch .env
```

根据实际环境修改 `.env`。不要提交 `.env`、数据库密码、Supabase Service Role、SMTP 授权码或模型密钥。

### Docker 启动

```bash
docker-compose --project-name insight-web --file compose.yaml up --detach --build
bash scripts/health-check.sh full
```

访问：

- Web：<http://localhost:3000>
- API：<http://localhost:8000>
- OpenAPI：<http://localhost:8000/docs>

首次启动时后端会补齐运行所需表、字段和索引；生产数据库结构仍应以迁移记录和 [数据库契约](doc/database-schema.md) 为准。

## 7. 环境变量

### 主系统必需配置

```dotenv
# Supabase / PostgreSQL
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
DATABASE_URL=postgresql://user:password@host:6543/postgres
DIRECT_URL=postgresql://user:password@host:5432/postgres

# 应用
BASE_URL=http://localhost:3000
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
STARTUP_CATCHUP_ENABLED=true
```

### 后台 AI Pipeline

```dotenv
CHAT_API_URL=https://your-provider.example/v1/chat/completions
CHAT_API_KEY=your-api-key
CHAT_MODEL=your-model
```

未配置 AI 时，采集、浏览和 Workbench 仍可运行；AI 评估、摘要和研报能力会不可用或保持已有结果。

### 邮件订阅

```dotenv
SMTP_HOST=smtp.example.com
SMTP_PORT=465
SMTP_USER=sender@example.com
SMTP_PASSWORD=your-smtp-authorization-code
EMAIL_FROM=sender@example.com
EMAIL_TO=optional-default-recipient@example.com
```

订阅者、投递星期和时间由管理员在系统设置中维护。调度器每分钟检查到期计划，同一订阅者同一天只发送一次。

### Insight-Agent / SSO

```dotenv
NEXT_PUBLIC_OPENCODE_URL=http://your-server:4096
OPENCODE_PUBLIC_URL=http://your-server:4096
OPENCODE_ALLOWED_EMAIL=admin@example.com
OPENCODE_COOKIE_SECURE=false
```

生产 HTTPS 环境必须将 `OPENCODE_COOKIE_SECURE` 设为 `true`。SSO 共享密钥通过只读 secret file 挂载，不应写入前端变量或提交到仓库。

## 8. 本地开发

需要 Python 3.11+ 和 Node.js 22+。

```bash
# Terminal 1：后端
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
STARTUP_CATCHUP_ENABLED=false uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

```bash
# Terminal 2：前端
cd frontend
npm ci
API_PROXY_TARGET=http://127.0.0.1:8000 npm run dev
```

前端通过同源 `/api/*` 访问 FastAPI，生产环境由 Next.js rewrite 转发到 `http://backend:8000`。

## 9. 定时任务与数据更新

主后端内运行一个 APScheduler 实例：

| 时间 | 任务 |
|---|---|
| 每天 09:00 | GitHub 技术热点采集、阿里云解决方案目录对比 |
| 每天 09:03 | 技术项目价值评估 |
| 每天 09:04 | 项目用途速读生成 |
| 每天 03:00 | 历史数据清理 |
| 每分钟 | 检查订阅者邮件投递计划 |

调度器当前按单 API 实例设计。若未来横向扩容 FastAPI，必须先增加数据库租约或独立调度服务，避免多实例重复执行任务。

## 10. Insight-Agent 独立运维

Insight-Agent Runtime 不随主系统一起启停：

```bash
sudo bash deploy/opencode/manage.sh start
sudo bash deploy/opencode/manage.sh health
sudo bash deploy/opencode/manage.sh status
sudo bash deploy/opencode/manage.sh logs
sudo bash deploy/opencode/manage.sh stop
sudo bash deploy/opencode/manage.sh upgrade
```

默认运维边界：

- 凭据：`/etc/insight-opencode/opencode.env`
- 持久化根目录：`/var/lib/insight-opencode/`
- Session、配置和 Workspace 独立持久化。
- 不挂载生产 `.env`、数据库凭据、Docker Socket 或 InsightPro 生产目录。
- Gateway 停止只影响 Insight-Agent，不影响 InsightPro readiness。

完整说明见 [Insight-Agent 文档](services/insight-agent/README.md)。

## 11. 测试与质量门禁

```bash
# 后端
cd backend
STARTUP_CATCHUP_ENABLED=false python -m pytest -q

# 前端
cd ../frontend
npm run lint
npx prisma validate
npm run build

# 已部署实例
cd ..
bash scripts/health-check.sh infra
bash scripts/health-check.sh full
```

`infra` 检查前端、后端进程和同源 API 代理；`full` 进一步检查 PostgreSQL、数据新鲜度、技术热点和价值评估数据契约。Insight-Agent 不属于主系统 full health 的依赖项。

截至 2026-08-27，当前主分支验证基线为：

- 后端 Pytest：40 项通过。
- 前端 ESLint：通过。
- TypeScript 与 Next.js production build：20 个页面路由通过。
- Docker 主系统端到端健康检查：通过。

## 12. 生产部署与回滚

```bash
sudo bash scripts/deploy-docker.sh
```

发布脚本会依次执行：

1. 获取部署锁，防止并发发布。
2. 校验 Docker 与 Compose 配置。
3. 执行后端测试和前端 ESLint。
4. 构建固定为 `0.4.0` 的前后端镜像。
5. 切换 systemd 守护模式并启动 Compose 服务。
6. 在 180 秒内等待 full health 通过。
7. 健康失败时停止新容器并恢复历史 systemd 部署。

部署脚本只管理 `insight-web` Compose project，不管理 Insight-Agent 的独立 Compose project。

## 13. 安全边界

- 浏览器只持有 Supabase anon key 和用户 Session；Service Role 仅存在于后端。
- Workbench 查询必须携带当前用户身份，并在 Repository 查询中限制 `user_id`。
- 管理员接口由后端 `require_admin` 校验，不能依赖隐藏菜单。
- Insight-Agent SSO ticket 有短有效期、只能消费一次，并在服务端换取 HttpOnly Gateway Session。
- Insight-Agent 不得读取生产 `.env`、Supabase Service Role、数据库密码、SMTP 密钥或生产模型密钥。
- Agent Workspace 与生产仓库分离；Workspace 内的写操作不会直接修改或部署生产系统。
- 当前 Agent 单实例不具备正式多租户隔离能力，因此只授权一个管理员。

安全细节见 [Insight-Agent SECURITY](services/insight-agent/SECURITY.md) 和 [技术架构与业务架构清单](doc/技术架构与业务架构清单.md)。

## 14. Git 工作流

推荐使用普通合并策略，不在共享 `main` 上执行不必要的 rebase：

```bash
git status
git add path/to/changed-file
git commit -m "feat: describe the change"
git pull --no-rebase origin main
git push origin main
```

优先明确列出要暂存的文件，避免使用 `git add .` 将 `.env`、日志或个人临时文件误提交。

## 15. 当前边界

本版本明确不包含：

- 行业洞察、政策雷达、招标信息、云厂商洞察。
- Task、Knowledge、RAG、向量数据库、工作流引擎、Kanban、甘特图。
- Insight/Solution/Requirement 自动注入 Agent 上下文。
- Agent 自动写业务数据库、提交 Git 或执行部署。
- OpenCode Core 修改、自研 Agent Chat UI、多 Agent 和 Workflow 编排。
- 安全的 Insight-Agent 多用户共享实例。

## 16. 文档索引

- [技术架构与业务架构清单](doc/技术架构与业务架构清单.md)：业务边界、组件、数据流、API、权限和风险。
- [数据库契约](doc/database-schema.md)：业务表、字段、约束和数据关系。
- [运维手册](doc/运维手册.md)：安装、部署、巡检、补跑、回滚和故障处理。
- [整改方案](doc/整改方案.md)：仍需处理的技术债与触发条件。
- [版本日志](log/versions.md)：项目演进与已完成变更。
- [Insight-Agent README](services/insight-agent/README.md)：Agent 产品能力和运维入口。
- [Insight-Agent Architecture](services/insight-agent/ARCHITECTURE.md)：服务、网络、Session 和数据边界。
- [Insight-Agent Security](services/insight-agent/SECURITY.md)：权限、Secret 和多用户风险。
- [Insight-Agent Deployment](services/insight-agent/DEPLOYMENT.md)：独立 Compose、持久化、升级与回滚。

---

InsightPro `v0.4.0` 的定位始终是技术解决方案洞察平台：先发现值得关注的技术，再把洞察转化为可执行的 Requirement 和可管理的 Solution。
