# 商业洞察平台 (Business Insights Platform)

当前版本：**0.1.0**

这是一个面向商业市场与云服务竞争分析场景的 AI 商业洞察平台。项目采用前后端分离架构，围绕“今日洞察、友商洞察、热点追踪、数据大屏、深度研报”构建一个可持续扩展的商业情报工作台。

## 项目目标

- 聚合最新行业、热点、新闻、政策、商机信息
- 对 AWS、微软 Azure、阿里云、腾讯云、火山云等友商做对比分析
- 面向华为云输出竞争力判断与机会点建议
- 通过 AI 生成结构化商业洞察和深度研报
- 通过首页看板和数据大屏完成可视化展示

## 当前能力

### 前端能力

- 首页“今日商业洞察”总览
- 行业全景、案例库、热点追踪、友商洞察、政策法规、商业快讯、增长机会页面
- 商机发现模块：市场情报、需求挖掘、招标信息
- 数据大屏、历史日报、深度研报、系统设置
- 响应式侧边栏与移动导航

### 后端能力

- FastAPI 服务
- 百度热搜实时抓取与降级读取
- GitHub Trending 实时抓取、历史记录查询、手动刷新
- APScheduler 定时任务
- DeepSeek 兼容 OpenAI SDK 的 AI 分析任务接口
- 本地 SQLite 数据缓存

## 技术栈

- **前端**：Next.js App Router、React、TypeScript、Tailwind CSS、Lucide React、Recharts
- **后端**：FastAPI、Uvicorn、Pydantic、Requests、BeautifulSoup4、APScheduler
- **AI**：DeepSeek API、OpenAI SDK、LangChain
- **数据库**：Supabase PostgreSQL + Prisma（规划中），SQLite（当前缓存）

## 项目结构

```text
insight-web/
├── backend/                         # FastAPI 后端与数据抓取
│   ├── main.py                      # 主 API、爬虫、调度器
│   ├── deep_searcher_integration.py # 检索/知识增强相关集成
│   ├── requirements.txt             # Python 依赖
│   └── trending.db                  # 本地缓存数据库
├── frontend/                        # Next.js 前端
│   ├── src/app/                     # 页面路由
│   ├── src/components/              # 复用组件
│   ├── src/utils/                   # 工具与 Supabase 客户端
│   ├── prisma/                      # Prisma schema
│   └── package.json                 # 前端依赖与脚本
├── demo/                            # 参考项目
├── log/                             # 项目日志
├── RESEARCH/                        # 研究资料
├── README.md                        # 项目说明
└── .gitignore                       # Git 忽略规则
```

## 主要页面

| 页面 | 路径 | 说明 |
|------|------|------|
| 今日洞察 | `/` | 首页总览，展示各子板块摘要与实时热搜 |
| 行业全景 | `/insights/industry` | 六大行业动态与外部信源 |
| 案例库 | `/insights/industry/cases` | 行业案例与上云实践 |
| 热点追踪 | `/insights/hotspots` | GitHub Trending 实时与历史追踪 |
| 友商洞察 | `/insights/competitors` | 华为云 vs AWS/Azure/阿里云/腾讯云/火山云 |
| 政策法规 | `/insights/policy` | 商业市场政策影响分析 |
| 商业快讯 | `/insights/news` | 商业新闻卡片与外链 |
| 增长机会 | `/insights/opportunities` | 客群机会与行动建议 |
| 市场情报 | `/insights/market` | 市场侧商机信息 |
| 需求挖掘 | `/insights/demand` | 客户需求线索分析 |
| 招标信息 | `/insights/bidding` | 招投标情报页面 |
| 数据大屏 | `/dashboard` | 运营指标与趋势图表 |
| 深度研报 | `/reports` | AI 结构化报告展示 |
| 历史日报 | `/history` | 历史洞察归档 |
| 系统设置 | `/settings` | 基础配置与状态管理 |

## 后端接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | 服务健康检查 |
| GET | `/api/baidu-hotsearch` | 百度实时热搜 |
| GET | `/api/github-trending` | GitHub Trending 数据 |
| GET | `/api/github-trending/history` | GitHub Trending 历史记录 |
| POST | `/api/github-trending/refresh` | 手动刷新 GitHub Trending |
| GET | `/api/competitors` | 友商洞察数据 |
| GET | `/api/dashboard/stats` | 数据大屏统计数据 |
| GET | `/api/daily-insight` | 今日洞察数据 |
| POST | `/api/tasks/analyze` | AI 洞察分析任务 |

## 环境变量

根目录 `.env` 示例：

```env
DEEPSEEK_API_KEY=your_deepseek_api_key
DEEPSEEK_API_BASE=https://api.deepseek.com

NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=your_supabase_publishable_key

DATABASE_URL=postgresql://...
DIRECT_URL=postgresql://...
```

## 本地启动

### 1. 启动后端

```bash
cd backend
python -m venv venv
venv\Scripts\activate
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

## 当前开发状态

- 已完成：前后端基础骨架、主要页面结构、热搜与 GitHub Trending 抓取、基础数据大屏、友商洞察内容框架
- 进行中：首页子版块最新内容替换、看板增强、友商洞察深化、数据大屏真实数据接入
- 待完善：每日 AI 洞察落库、Supabase 持久化、更多实时数据源、导出与分享能力

## 版本说明

### 0.1.0

- 完成商业洞察平台 MVP 骨架
- 建立前端多页面导航与核心布局
- 接入百度热搜与 GitHub Trending 抓取能力
- 搭建友商洞察、数据大屏、深度研报等基础页面
- 更新根目录 README 以匹配当前项目状态
