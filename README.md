# 商业洞察平台 (InsightPro · Business Intelligence Platform)

当前版本：**0.0.21**

一个面向商业市场与云服务竞争分析场景的 AI 商业洞察平台。项目采用前后端分离架构，Docker Compose 生产部署，围绕"首页洞察、热点追踪、行业洞察、政策法规"提供可持续扩展的商业情报工作台。

---

## 目录

- [项目目标](#项目目标)
- [当前能力](#当前能力)
- [技术栈](#技术栈)
- [快速开始（Docker 生产部署）](#快速开始docker-生产部署)
- [开发环境启动](#开发环境启动)
- [项目结构](#项目结构)
- [主要页面](#主要页面)
- [后端接口](#后端接口)
- [环境变量](#环境变量)
- [运维要点](#运维要点)
- [版本记录](#版本记录)

---

## 项目目标

- 聚合最新行业、热点、新闻、政策、商机信息
- 对 AWS、微软 Azure、阿里云、腾讯云、火山云等友商做对比分析
- 面向华为云输出竞争力判断与机会点建议
- 通过 AI 生成结构化商业洞察和深度研报
- 通过首页看板完成可视化展示

## 当前能力

### 前端能力

- 首页"今日商业洞察"总览
- 行业全景、热点追踪、商业快讯、政策法规、商机机会
- 招标信息、需求挖掘、友商洞察
- 数据大屏、深度研报、历史日报、系统设置
- 响应式侧边栏与移动导航
- 智能聊天助手（全局挂载）

### 后端能力

- FastAPI 服务 + Uvicorn
- GitHub Trending 实时抓取、历史记录查询、手动刷新
- 百度热搜实时抓取与降级读取
- 多项采集器：新闻、政策、厂商、招标、需求信号
- 技术业务价值 AI 评估（DeepSeek API）
- APScheduler 定时任务
- Supabase PostgreSQL 持久化 + 缓存降级
- 同源 API 代理（前端通过 Next.js rewrite 转发，不直连后端端口）
- 启动补跑（按依赖顺序补齐当天缺失数据，PostgreSQL advisory lock 防重复）
- Docker healthcheck + systemd 健康守护

## 技术栈

| 层 | 技术 |
|---|------|
| **前端** | Next.js 16 (App Router)、React 19、TypeScript、Tailwind CSS、Lucide React、Recharts |
| **后端** | FastAPI、Uvicorn、Pydantic v2、httpx、BeautifulSoup4、APScheduler |
| **AI** | DeepSeek API（OpenAI SDK 兼容）、DeepSearcher（可选增强） |
| **数据库** | Supabase PostgreSQL + Prisma（生产）；SQLite（开发/降级） |
| **部署** | Docker Compose（多阶段构建）、systemd（开机自启）、Docker healthcheck |

## 快速开始（Docker 生产部署）

### 前置条件

- Docker Engine 18.09+（本项目兼容 18.09，生产建议 20.10+）
- `docker-compose` v2+（参见 `scripts/install-docker-compose.sh`）
- 根目录 `.env` 文件已配置（参见[环境变量](#环境变量)）

### 首次部署

```bash
# 1. 安装 Docker Compose（如尚未安装）
sudo ./scripts/install-docker-compose.sh

# 2. 测试 → 构建 → 切换 → 端到端验收（失败自动回退旧部署）
sudo ./scripts/deploy-docker.sh
```

### 日常运维

```bash
# 查看容器状态
export DOCKER_API_VERSION=1.39
docker-compose -p insight-web -f compose.yaml ps

# 查看日志
docker-compose -p insight-web -f compose.yaml logs --tail 100

# 手动重启
docker-compose -p insight-web -f compose.yaml restart

# 完整健康验收
./scripts/health-check.sh full
```

### 开机自启（已配置）

系统重启后，Docker 平台服务自动拉起，无需人工干预：

```
systemd (PID 1)
 ├─ docker.service                         (enabled)  ← Docker daemon
 ├─ insight-docker-compose.service         (enabled)  ← 开机执行 docker-compose up
 └─ insight-docker-health-guard.timer     (enabled)  ← 每10分钟巡检 + 自动修复
```

> **注意**：当前 Docker Engine 18.09 的 `restart: unless-stopped` 在 daemon 重启后不可靠，因此使用 systemd 服务替代。健康守护定时器会在开机 2 分钟后首次巡检，之后每 10 分钟检查一次，发现异常自动清理旧状态并重建容器。

详细运维说明见 [`doc/运维手册.md`](doc/运维手册.md)。

## 开发环境启动

### 1. 启动后端

```bash
cd backend
python -m venv venv
source venv/bin/activate      # Linux/Mac
# venv\Scripts\activate       # Windows
pip install -r requirements.txt
python main.py
```

默认地址：`http://localhost:8000`

### 2. 启动前端

```bash
cd frontend
npm install
npm run dev
```

默认地址：`http://localhost:3000`

> 开发模式下前端通过 `NEXT_PUBLIC_API_URL` 直连后端；生产 Docker 部署通过 Next.js rewrite 同源代理转发。

## 项目结构

```text
insight-web/
├── backend/                         # FastAPI 后端
│   ├── main.py                      # 入口、爬虫调度、API 路由注册
│   ├── crawlers.py                  # 各数据源采集器
│   ├── deep_searcher_integration.py # RAG/知识检索集成（可选）
│   ├── maintenance.py               # 运维 CLI（数据补跑等）
│   ├── routers/                     # API 路由模块
│   ├── services/                    # 业务逻辑层
│   ├── tests/                       # 后端测试
│   ├── Dockerfile                   # 多阶段构建
│   └── requirements.txt             # Python 依赖
├── frontend/                        # Next.js 前端
│   ├── src/app/                     # 页面路由（App Router）
│   ├── src/components/              # 复用组件
│   ├── src/utils/                   # 工具函数与 Supabase 客户端
│   ├── public/                      # 静态资源（含聊天助手 chat.js）
│   ├── prisma/                      # Prisma schema
│   ├── Dockerfile                   # 多阶段构建
│   └── package.json                 # 前端依赖
├── scripts/                         # 部署与运维脚本
│   ├── deploy-docker.sh             # 标准发布门禁
│   ├── deploy.sh                    # systemd 旧部署（回退用）
│   ├── health-check.sh              # 健康检查
│   ├── docker-health-guard.sh       # Docker 健康守护巡检
│   └── install-docker-compose.sh    # Compose 安装脚本
├── deploy/systemd/                  # systemd unit 文件
├── doc/                             # 文档
├── log/                             # 版本日志与变更记录
├── compose.yaml                     # Docker Compose 编排
├── CLAUDE.md                        # 项目规则（AI 助手使用）
└── .env                             # 环境变量（不入库）
```

## 主要页面

| 页面 | 路径 | 说明 |
|------|------|------|
| 首页洞察 | `/` | 今日商业洞察总览，聚合各板块摘要 |
| 热点追踪 | `/insights/hotspots` | GitHub Trending 实时与历史追踪 |
| 行业洞察 | `/insights/industry` | 六大行业动态（含案例库） |
| 政策法规 | `/insights/policy` | 商业市场政策影响分析 |
| 商业快讯 | `/insights/news` | 商业新闻卡片与外链 |
| 友商洞察 | `/insights/competitors` | 华为云 vs AWS/Azure/阿里云/腾讯云/火山云 |
| 商机机会 | `/insights/opportunities` | 客群机会与行动建议 |
| 需求挖掘 | `/insights/demand` | 客户需求线索分析 |
| 招标信息 | `/insights/bidding` | 招投标情报 |
| 数据大屏 | `/dashboard` | 运营指标与趋势图表 |
| 深度研报 | `/reports` | AI 结构化报告 |
| 历史日报 | `/history` | 历史洞察归档 |
| 系统设置 | `/settings` | 基础配置与状态管理 |

## 后端接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | 服务健康检查 |
| GET | `/api/system/health/live` | 存活探针 |
| GET | `/api/system/health/ready` | 就绪探针（含数据新鲜度） |
| GET | `/api/data/freshness` | 九类数据集新鲜度状态 |
| GET | `/api/github-trending` | GitHub Trending 数据 |
| GET | `/api/github-trending/business-eval` | 技术业务价值评估 |
| GET | `/api/github-trending/history` | GitHub Trending 历史记录 |
| POST | `/api/github-trending/refresh` | 手动刷新 GitHub Trending |
| GET | `/api/baidu-hotsearch` | 百度实时热搜 |
| GET | `/api/competitors` | 友商洞察数据 |
| GET | `/api/dashboard/stats` | 数据大屏统计 |
| GET | `/api/daily-insight` | 今日洞察聚合 |
| GET | `/api/demand/trends` | 需求趋势分析 |
| GET | `/api/industry/overview` | 行业全景数据 |
| GET | `/api/reports` | 深度研报列表 |
| POST | `/api/chat` | 智能助手对话 |
| POST | `/api/chat/stream` | 智能助手流式对话 |
| POST | `/api/tasks/analyze` | AI 洞察分析任务 |

> 完整接口列表及鉴权要求见后端路由模块和测试用例。

## 环境变量

根目录 `.env` 配置示例：

```env
# AI
DEEPSEEK_API_KEY=sk-your_key
DEEPSEEK_API_BASE=https://api.deepseek.com

# Supabase
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key

# CORS（允许多个前端来源）
CORS_ORIGINS=http://localhost:3000,http://192.168.0.191:3000

# 告警 Webhook（可选）
INSIGHT_ALERT_WEBHOOK=https://example.com/webhook

# 技术评估（可选）
AI_EVAL_MODEL=deepseek-chat
```

## 运维要点

| 操作 | 命令 |
|------|------|
| 查看容器状态 | `docker-compose -p insight-web ps` |
| 查看实时日志 | `docker-compose -p insight-web logs --tail 100 -f` |
| 重启服务 | `docker-compose -p insight-web restart` |
| 完整健康检查 | `./scripts/health-check.sh full` |
| 查看守护日志 | `journalctl -u insight-docker-health-guard.service -n 50 --no-pager` |
| 重新部署 | `sudo ./scripts/deploy-docker.sh` |

详细运维指南见 [`doc/运维手册.md`](doc/运维手册.md)。

## 版本记录

详细版本日志见 [`log/versions.md`](log/versions.md)。每次可验证整改后必须同步更新。
