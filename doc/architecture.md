# InsightPro（insight-web）平台架构全景

> 基线：2026-10-28。代码状态 = 提交 `aa1351a`（v1.1.0 之后仅 1 个提交）+ 未提交工作区（68 个跟踪文件 +1907/−670，另约 23 个新代码文件 +1529 行）。
> 运行镜像 `insight-web-backend/frontend:1.1.5-rc.2`（当日 07:51 启动）；Git 最新 tag `v1.1.1`；`frontend/package.json` 为 `1.1.5-rc.1`（版本漂移详见 §12）。
> 本文只描述可核实的现状，不含未实施的规划。所有端点、任务、容器、systemd 单元均从代码与本机运行状态直接枚举。

---

## 目录

- §0 全景总图
- §1 部署拓扑（容器 / 端口 / 网络 / 密钥 / systemd / 同机邻居）
- §2 请求全链路（中间件栈顺序 / 四类请求路径 / 页面快照机制）
- §3 认证与安全体系（身份矩阵 / 登录流 / Hermes SSO / 守卫逐条判定）
- §4 后端架构（应用装配 / 启动时序 / 19 个路由模块 169 个端点全表 / 57 个服务模块分域）
- §5 数据层（Supabase 组件 / 38 个 Alembic 迁移史 / 核心数据域）
- §6 数据管道与调度（16 个定时任务 / 每日流水线时间线 / 源注册表与 17 类适配器）
- §7 前端架构（构建与代理 / 44 个页面树 / 请求层分裂 / 组件与 lib / 全局助手）
- §8 Agent 与 AI 体系（三个 Agent 面 / Hermes 进程模型 / Runtime / RAG / 深度检索）
- §9 邮件体系
- §10 运维体系（看门狗 / 部署流程 / 健康检查 / 版本治理）
- §11 版本与代码状态快照
- §12 已知问题与断点（含「前端无数据」401 根因）
- 附录 A 配置字段全景 · 附录 B 术语表

---

## §0 全景总图

```
                    ┌─────────────────────────────────────────────────────────────────────────────────────┐
                    │                    宿主机 159.138.89.233 · Linux HCE · Docker 引擎                     │
                    │                                                                                 │
  ┌──────────┐      │   insight-network ────────────────────────────────────────────────────────────      │
  │          │ :3000│  ┌──────────────────────┐   /api/* rewrite        ┌──────────────────────────┐     │
  │  浏览器   ├──────┼─▶│ insight-frontend     │ ──────────────────────▶ │ insight-backend          │     │
  │ (管理员)  │      │  │ Next.js standalone   │   (Next rewrites →      │ FastAPI + APScheduler    │     │
  │          │ :4096│  │ host 3000→3000       │    insight-backend:8000)│ host 8000→8000           │     │
  │          ├────┐ │  │                      │                         │                          │     │
  └──────────┘    │ │  │  · proxy.ts 全站门禁  │ ◀────────────────────   │  4 层中间件               │     │
                  │ │  │    (非管理员→登录页)  │   16 个定时任务内调      │  19 个路由模块/169 端点    │     │
                  │ │  │  · /supabase/* 代理   │                         │  57 个服务模块            │     │
                  │ │  └──────────┬───────────┘                         │  2 个爬虫模块             │     │
                  │ │             │ /supabase/* rewrite                  │     │                    │     │
                  │ │             ▼                                      │     │ psycopg2          │     │
                  │ │  ┌──────────────────────┐   Bearer JWT (gotrue)    │     │                    │     │
                  │ │  │ supabase-envoy :8000 │ ◀────────────────────── │ ────┘ DIRECT_URL/DATABASE │     │
                  │ │  │ (Supabase API 边缘)   │   service-key 直连      │      _URL (pooler 二选一)│     │
                  │ │  └──────────┬───────────┘                         └──────┬───────────────────┘     │
                  │ │             ▼                                            │                         │
                  │ │  ┌─────────────────────────────────┐                  │  ┌────────────────────┐   │
                  │ │  │ supabase 容器栈 (12 容器)         │◀─────────────────┘  │ 外部 AI 服务          │   │
                  │ │  │ gotrue auth · postgres 17.6.1.136│  5432 直连         │ · 聊天 LLM (OpenAI 兼 │   │
                  │ │  │ postgrest v14.18 · realtime      │                    │   容, 运行时可切换)     │   │
                  │ │  │ storage · imgproxy · meta        │                    │ · Embedding API       │   │
                  │ │  │ studio · supavisor 池化 15432    │                    │ · Reranker API        │   │
                  │ │  └─────────────────────────────────┘                    └────────────────────┘   │
                  │ │                                                                                    │
                  │ │  hermes 侧网络 (不在本仓库 compose 内, 由 insight-hermes.service 管理)                │
                  │ │  ┌────────────────────────┐    auth_request 校验     ┌──────────────────────┐      │
                  │ ├─▶│ insight-hermes-gateway  │ ──────────────────────▶ │ insight-hermes        │      │
                  │ │  │ nginx, host 4096→8080   │   (回调后端 verify 端点) │ v2026.8.19            │      │
                  │ │  │ 未登录 302 → 前端登录页  │                         │ · 每回合一个 Python    │      │
                  │ │  │ 通过后反代 Hermes :4096  │                         │   Agent 进程 (NDJSON)  │      │
                  │ │  └────────────────────────┘                         │ · runtime-manager.mjs  │      │
                  │ │              ▲ cookie insight_agent_session          │ · 最多 6 个活跃回合     │      │
                  │ │              │ SSO 票据 → callback → 网关会话         └──────────┬───────────┘      │
                  │ │                                                       └── 聊天 LLM (外部网关) ──▶ 外部   │
                  │ │                                                                                    │
                  │ │  systemd: insight-web.target · insight-docker-compose.service · insight-hermes.service │
                  │ │          insight-docker-health-guard.timer (~5min 看门狗) · insight-health-guard.timer│
                  │ │  密钥文件: /etc/insight-hermes/backend-gateway.secret (挂载至前后端容器 + Hermes 网关)  │
                  │ │                                                                                    │
                  │ │  同机邻居(独立项目): daily_news 栈(caddy 80/443/8181) · solution-patrol :7272            │
                  │ │                      solution-practice-workbench :8088 · server-inventory               │
                  │ └────────────────────────────────────────────────────────────────────────────────────    │
                  └─────────────────────────────────────────────────────────────────────────────────────────┘
                                        │
                     ┌──────────────────┼───────────────────────┐
                     ▼                  ▼                       ▼
              互联网情报源           邮件触达                外部 AI
   GitHub Trending / Search    SMTP (可后台配置)      聊天 / 向量 / 重排
   HackerNews · HuggingFace                          (地址与密钥均支持
   arXiv · ProductHunt                                运行时热切换)
   RSS · api_json · html_links
   阿里云/华为云方案页
   百度热搜 · 知乎/CSDN/腾讯社区
   友商官网动态 · AI 应用官方渠道
```

一句话概括系统职责：**从 17 类外部源按源级 cron 采集 AI 产业情报，经 AI 加工（评估/事件分析/板块洞察/每日简讯）写入 Supabase Postgres，以"每日页面快照 + 管理端实时 API"两种口径对外服务，并配套三面 Agent（站点助手 / 嵌入式 Insight-Agent / 独立 Hermes 空间）与订阅邮件体系。**

---

## §1 部署拓扑

### 1.1 本项目容器（compose.yaml，project name = insight-web）

| 容器 | 镜像 | 宿主端口 | 网络 | 关键挂载/环境 |
|---|---|---|---|---|
| insight-backend | insight-web-backend:1.1.5-rc.2 | 0.0.0.0:8000→8000 | insight-network + supabase-network | env_file .env；TZ=Asia/Shanghai；`SCHEDULER_ENABLED=true`；`STARTUP_CATCHUP_ENABLED=false`；`STARTUP_SCHEMA_ENABLED=false`；`REQUIREMENT_ABSORPTION_ON_STARTUP=true`；挂载 backend-gateway.secret → /run/secrets/insight-hermes-gateway:ro；健康检查打 /api/system/health/live |
| insight-frontend | insight-web-frontend:1.1.5-rc.2 | 0.0.0.0:3000→3000 | insight-network + supabase-network | 构建参数注入 NEXT_PUBLIC_SUPABASE_URL/ANON_KEY、API_PROXY_TARGET、SUPABASE_INTERNAL_URL；同样挂载网关密钥；健康检查用 node fetch live；depends_on backend(service_healthy) |

`depends_on: condition: service_healthy` 保证前端只在后端存活探针通过后启动；两容器均为 `restart: unless-stopped`，日志 json-file 10m×3。

### 1.2 Supabase 容器栈（外部网络 insight-supabase_default，project 独立）

| 容器 | 镜像 | 职责 |
|---|---|---|
| supabase-envoy | envoyproxy/envoy:v1.39.1 | Supabase API 边缘网关（内部 :8000，宿主 127.0.0.1:18000）——前端 `/supabase/*` rewrite 的目标 |
| supabase-auth | supabase/gotrue:v2.197.0 | 用户认证（signInWithPassword / get_user / admin API），JWT 签发 |
| supabase-db | supabase/postgres:17.6.1.136 | 业务主库（所有情报数据都在这里，非 Supabase 托管云） |
| supabase-pooler | supabase/supavisor:2.9.13 | 事务/会话池化（宿主 127.0.0.1:15432→5432、16543→6543），对应 DATABASE_URL |
| supabase-rest | postgrest/postgrest:v14.18 | PostgREST 自动 REST |
| realtime-dev.supabase-realtime | supabase/realtime:v2.143.3 | 实时订阅 |
| supabase-storage | supabase/storage-api:v1.81.0 | 对象存储 |
| supabase-imgproxy | darthsim/imgproxy:v3.31.4 | 图片处理 |
| supabase-meta | supabase/postgres-meta:v0.100.0 | 元数据 API |
| supabase-studio | supabase/studio:2026.10.12 | 管理台（内部 :3000，未对宿主发布） |

后端数据访问走 `db.py` 的 psycopg2（优先 DIRECT_URL 免池化 DDL，退 DATABASE_URL 池化）；`trending.db`（SQLite）仅作一次性历史迁移源保留，其 -wal/-shm 文件目前未被 git 忽略（见 §12）。

### 1.3 Hermes / Agent 网关（独立于本仓库 compose）

| 容器 | 镜像 | 说明 |
|---|---|---|
| insight-hermes-gateway | nginxinc/nginx-unprivileged:1.29.4-alpine | 宿主 4096→8080。每个请求先 `auth_request` 打后端 `/api/auth/agent/verify`（携带网关密钥头 + insight_agent_session cookie），校验通过后反代 Hermes 容器；未登录 302 跳前端登录页并带 next=/auth/agent。CSP 限定 frame-ancestors 为前端来源 |
| insight-hermes | insight-hermes:v2026.8.19 | 上游 Hermes Agent 引擎。环境要点：CHAT_MODEL=deepseek-v4-flash-0731 经 OpenAI 兼容网关；HERMES_MAX_ACTIVE=6；HERMES_IDLE_SECONDS=1800；INSIGHT_PUBLIC_API_URL 指向宿主 8000；数据根 /srv/insight-agent；内部跑 node /opt/insight-agent/runtime-manager.mjs 作为隔离运行时管理器 |

密钥现状：网关密钥以文件 `/etc/insight-hermes/backend-gateway.secret` 挂载给三个容器（做法正确）；但 Hermes 容器的聊天 API key 以明文 env 注入，`docker inspect` 可见（见 §12 风险项）。

### 1.4 systemd 单元

| 单元 | 类型 | 职责 |
|---|---|---|
| insight-web.target | target | 聚合 Requires=insight-backend.service + insight-frontend.service（旧直启单元的遗留聚合） |
| insight-docker-compose.service | oneshot(RemainAfterExit) | 实际拉起/停止 compose 双容器（down --remove-orphans → up -d） |
| insight-hermes.service | service | Hermes + 网关容器组 |
| insight-docker-health-guard.service + .timer | timer | ~5 分钟一轮：跑 health-check full，失败则尝试数据新鲜度修复并报 CRITICAL |
| insight-health-guard.service + .timer | timer | 旧版健康守护（并存） |

注意：宿主机上另可观察到一个 `uvicorn backend.main:app --port 8999` 直跑进程（与本仓库模块同名，来源待确认，疑似旧 insight-backend.service 直启残留），与容器内 8000 服务并存。

### 1.5 同机邻居（非本项目，仅端口/资源共存）

- daily_news 全栈：caddy 占宿主 80/443/8181，另有 web/api/scheduler/worker/postgres/redis（均未占 3000/8000）
- solution-patrol（:7272）、solution-practice-workbench（:8088）、server-inventory

本项目的对外暴露面因此是三个端口：3000（前端）、8000（后端 API）、4096（Agent 网关）。

---

## §2 请求全链路

### 2.1 中间件栈（顺序是理解一切 401/503 的关键）

Starlette 规则：**后注册的先执行**。main.py 中的注册顺序与执行顺序如下：

```
请求
 │
 ▼ ① CORSMiddleware                (main.py:169 add_middleware, 最后注册 → 最外层)
 │
 ▼ ② admin_api_guard               (main.py:146 @app.middleware, 未提交新代码)
 │    匿名 /api/* 一律 401（详见 §3.4）
 │
 ▼ ③ published_page_reads          (main.py:110 @app.middleware)
 │    GET 命中 30 个快照路径 → 直接回放 page_snapshots 表当日内容
 │    POST 命中 6 个 refresh 端点 → 触发快照重发布
 │
 ▼ ④ SanitizingErrorHandler        (middleware/error_handler.py, 最先注册 → 最内层)
 │
 ▼ 路由分发 → 依赖注入(require_auth/require_admin) → 服务层 → db.py → Postgres
```

`admin_api_guard` 在 `published_page_reads` 外层，意味着**匿名请求根本轮不到快照回放**——这正是 §12 中「前端无数据」的结构性根因。

### 2.2 四类典型请求路径

| 路径 | 凭据 | 经历 | 结果 |
|---|---|---|---|
| A. 匿名浏览首页数据 | 无 | ①CORS→②guard 判定无 Bearer→401 | 前端空态（当前线上症状） |
| B. 管理员登录后浏览 | Supabase JWT | ②guard 调 supabase.auth.get_user 校验 app_metadata.role=admin 且非 disabled→放行→③若命中快照路径回放快照 | 200（32 个已迁移 authenticatedFetch 的页面均正常） |
| C. 快照自发布（进程内） | x-insight-internal-key=网关密钥 | httpx ASGITransport 进程内自调 30 个路径，guard 对 PATH_TO_PAGE 且密钥匹配者放行 | 快照落库（历史上曾因无此头而 401，rc.2 镜像已含修复） |
| D. Hermes 网关会话 | cookie insight_agent_session | nginx auth_request → 后端 /api/auth/agent/verify（校验网关密钥头+cookie）→ 回 X-Insight-* 身份头 → 反代 Hermes | Agent 空间可用 |

另有根级旁路：`/api/pages/{page}/latest` 聚合一页多路径快照；`/api/system/health/live` 无外部依赖、`/api/system/health/ready` 检查 DB+新鲜度+技术热点。

### 2.3 页面快照机制（读路径与写路径彻底分离）

```
写路径（每天 09:50 定时任务 page_snapshots_daily，或任一 refresh 端点 POST 后触发）：
  publish_page_snapshots()
    ├─ BUILDING ContextVar 置 True（期间读路径回 503，避免读到半新半旧）
    ├─ httpx.ASGITransport 进程内并发 GET 全部 30 个路径（带内部密钥头）
    ├─ 按 (snapshot_date=今天, page=路径) UPSERT page_snapshots，冲突时 version+1
    └─ finally 复位 BUILDING

读路径（published_page_reads 中间件）：
  GET 命中 PATH_TO_PAGE 且非 BUILDING
    ├─ 查当日行 → 返回 content + X-Page-Snapshot-Date / X-Page-Snapshot-Id 头
    └─ 无当日行 → 503 "Daily page snapshot is being prepared"

兜底：
  启动线程 bootstrap_page_snapshots_sync：任一路径无快照则全量补发
  /api/pages/{page}/latest：按页面聚合多路径快照（供前端一次性取整页数据）
```

6 个页面共 30 条快照路径：home 1 条、technology 13 条（trending 三周期、business-eval 双语、history 3 周期×2 语言、板块洞察）、applications 4 条、solutions 3 条、community 4 条、competitors 5 条。

---

## §3 认证与安全体系

### 3.1 身份与凭据矩阵

| 主体 | 身份载体 | 校验方 | 判定条件 |
|---|---|---|---|
| 匿名外部请求 | 无 | admin_api_guard | /api/* 一律 401（仅白名单 5 端点 + internal-key 快照旁路） |
| 管理员（浏览器） | Supabase JWT（Authorization: Bearer） | admin_api_guard / require_auth / require_admin | supabase.auth.get_user(token) 成功且 app_metadata.role=admin 且 status≠disabled |
| 管理员（前端侧） | Supabase 会话 cookie（auth-cookie 工具） | proxy.ts 全站门禁 | 非 admin 用户一律 302 → /admin/login?next=… |
| 进程内快照发布 | x-insight-internal-key 头 | admin_api_guard | 值 = HERMES_SSO_SECRET 且路径 ∈ PATH_TO_PAGE |
| Hermes 网关（→后端） | X-Insight-Gateway-Secret 头 | /api/auth/agent/verify | hmac.compare_digest 与 _gateway_secret() 比对 |
| Hermes 网关（→用户） | insight_agent_session cookie (HttpOnly) | 后端 verify → agent_sso_service | 网关会话表内未过期、未撤销 |
| Hermes Agent 进程 | X-Insight-Runtime-Secret 头 | runtime-manager.mjs | 值 = HERMES_SSO_SECRET（同一密钥三用） |
| 后端 → 聊天/向量/重排 AI | Bearer CHAT_API_KEY 等 | 外部 AI 网关 | 设置页可运行时热切换（runtime_config_service / embedding_config_service） |

管理员判定逻辑三处复用同一规则（`app_metadata.role == "admin" && status != "disabled"`）：后端 `_is_internal_member`、前端 `member()`、网关侧由后端 verify 输出角色头。成员管理通过 Supabase admin API（invite/patch disabled）。

### 3.2 登录流（当前）

```
/admin/login 页面
  → AuthProvider.signIn: supabase.auth.signInWithPassword
     (本地账号自动补 @insightpro.local 后缀)
  → getUser 确认 admin → 会话写入 Supabase auth-cookie
  → proxy.ts 拦截所有非 /admin/login、非 /api、非 /supabase 路由：
     非 admin → 302 /admin/login?next=<原路径>
```

### 3.3 Hermes SSO 流（AI 空间）

```
前端 POST /api/auth/agent/ticket (Bearer JWT)
  → 校验发起人是活跃内部成员；若指定 target_user_id（admin 代入他人空间）与 agent_session_id 也一并校验
  → 返回 redirect_url
浏览器 GET /api/auth/agent/callback?ticket=…  (x-insight-sso-ticket 头)
  → consume_ticket（一次性票据）
  → admin API 取 auth_account 与 agent_account（代入时二者不同）
  → create_gateway_session 写网关会话（TTL agent_sso_service.SESSION_TTL_SECONDS）
  → 303 重定向 HERMES_PUBLIC_URL/chat，并种 insight_agent_session + insight_agent_name cookie
此后所有 Agent 空间请求：
  nginx auth_request → GET /api/auth/agent/verify (X-Insight-Gateway-Secret + cookie)
  → 204 + X-Insight-User-Id / Agent-Role / Auth-Role / Display-Name / Agent-Session-Id 头
登出：POST /api/auth/agent/revoke → 撤销该用户全部网关会话 + 清 cookie
```

### 3.4 admin_api_guard 逐条判定（backend/main.py:146，未提交）

```
入口：所有请求
 1. 路径 ∈ {register, users/test, industry-news, policy/list, bidding/list, demand/signals}
    → 直接 404（旧对外功能下线伪装）
 2. full_path ∈ PATH_TO_PAGE 且 x-insight-internal-key == HERMES_SSO_SECRET → 放行（快照旁路）
 3. 路径非 /api/* → 放行（/、/api/pages/{page}/latest 例外见下）
 4. 路径 ∈ 白名单 {health/live, health/ready, auth/login, auth/agent/callback, auth/agent/verify} → 放行
 5. OPTIONS（CORS 预检）→ 放行
 6. require_admin 已被 dependency_overrides 覆盖（测试态）→ 改由依赖注入层校验
 7. 其余 /api/*：
    Authorization 非 Bearer 或 supabase 未配置 → 401 "Administrator login required"
    get_user 失败 → 401 "Login expired"
    非 internal_member → 401 "Administrator access required"
```

要点：`/api/pages/{page}/latest` 不在白名单也不在 PATH_TO_PAGE，**匿名调用同样被 401**——首页聚合接口也在断链之列。

---

## §4 后端架构

### 4.1 应用装配（main.py）

- 19 个路由模块经 `include_router` 挂载：18 个前缀 /api + intelligence_v2 前缀 /api/v2
- lifespan 启动序列（受三个开关控制）：
  1. `STARTUP_SCHEMA_ENABLED` → ensure_runtime_schema（含 REQUIREMENT_ABSORPTION_ON_STARTUP 吸收历史需求）
  2. recover_orphaned_runs（孤儿流水线/任务运行恢复）
  3. runtime_config_service.load() + embedding_config_service.load()（运行时 AI 配置热载入）
  4. `SCHEDULER_ENABLED` → BackgroundScheduler(Asia/Shanghai) 注册 16 任务 → start
  5. init_deep_searcher（失败仅告警不阻断）
  6. `STARTUP_SCHEMA_ENABLED` → init_crawler_tables
  7. `SCHEDULER_ENABLED` → 后台线程 bootstrap_page_snapshots_sync
  8. `STARTUP_CATCHUP_ENABLED` 且当前时间 ≥08:00 → 后台线程 run_startup_catchup（当前配置 false，重启后不补跑）
  9. yield 后 scheduler.shutdown()

### 4.2 路由 → 端点全表（169 个，按模块）

**auth/_login（6）**：POST /auth/login · GET /auth/me · GET /auth/users · POST /auth/users/invite · PATCH /auth/users/{id} · POST /auth/logout

**auth/_admin（13）**：GET /auth/agent-spaces · POST /auth/agent-spaces/{uid}/start · /stop · GET+POST /auth/admin/runtime-config · POST /auth/admin/runtime-config/verify · GET+PATCH /auth/admin/embedding-config · POST /auth/admin/embedding-config/verify · GET+POST /auth/public-knowledge · DELETE /auth/public-knowledge

**auth/_agent_sso（4）**：POST /auth/agent/ticket · GET /auth/agent/callback · GET /auth/agent/verify · POST /auth/agent/revoke

**dashboard（7）**：GET /radar/snapshot · GET /radar/intelligence · GET /dashboard/stats · GET /homepage/stats · GET /homepage/modules · GET /homepage/recommendation · （/dashboard/overview 见 §12 待核对）

**analytics（4）**：POST /track · GET /analytics · POST /track/batch · （/analytics/overview 见 §12 待核对）

**hotspots（12）**：GET /agent-launches · GET /agent-launches/progress · GET /daily-ai-brief · GET /daily-ai-brief/history · POST /daily-ai-brief/regenerate · GET /boards/{board}/daily-insight · GET /github-trending · GET /github-trending/history · POST /github-trending/refresh · GET /github-trending/business-eval · POST /github-trending/business-eval/refresh · GET /baidu-hotsearch

**search/reports（6）**：GET /search · POST /tasks/analyze · GET /tasks/{task_id} · GET /reports · GET /reports/{id} · DELETE /reports/{id}

**workbench（10，前缀 /workbench）**：GET /summary · GET/POST /requirements · GET/PUT/DELETE /requirements/{id} · POST/DELETE /requirements/{id}/solutions/{sid} · GET/POST /solutions · GET/PUT/DELETE /solutions/{id}

**crawling（4）**：POST /crawl/trigger · GET /crawl/status · GET /crawl/health · GET /data/freshness

**community（3）**：GET /community/insights · POST /community/insights/refresh · GET /community/insights/history

**competitors（4）**：GET /competitors · GET /competitors/summary · POST /competitors/refresh · GET /competitors/history

**solutions（5）**：GET /solutions/catalog · GET /solutions/aliyun · GET /solutions/catalog/{id} · POST /solutions/catalog/refresh · POST /solutions/aliyun/refresh

**email（14）**：GET+PUT /email/smtp-config · POST /email/smtp-config/test · GET /email/subscribers · POST /email/subscribe · PUT /email/subscribers/{id} · PUT /email/subscribers/{id}/subscriptions/{type} · POST /email/preference · PATCH /email/subscribers/{id}/language · DELETE /email/subscribers/{email} · POST /email/test · POST /email/subscribers/{id}/send · GET /email/preview · GET /email/snapshots/{id} · POST /email/send-now

**tasks（11）**：GET /admin/overview · GET /admin/collection · GET /admin/inspections · POST /admin/inspections/run · GET /admin/exports/{dataset} · GET /admin/tasks · POST /admin/tasks/{key}/run · PATCH /admin/tasks/daily_ai_brief/schedule · GET /admin/daily-ai-brief/versions · POST /admin/daily-ai-brief/retry-email · GET /admin/pipelines · POST /admin/pipelines/{domain}/run

**agent（27，前缀 /agent）**：GET /knowledge/search · GET /knowledge/overview · POST /knowledge/ask · POST /admin/knowledge/reindex · GET /context/{type}/{id} · GET /models · POST /practice-background · POST /suggestions · POST /sessions · POST /routes · GET /sessions/{id} · GET /internal/sessions/{id} · POST /sessions/{id}/context/refresh · PATCH /sessions/{id}/context · POST /sessions/{id}/artifacts · GET /artifacts · GET /artifacts/{id} · GET /artifacts/{id}/download · POST /artifacts/{id}/knowledge-request · GET /admin/artifacts/requests · POST /admin/artifacts/{id}/publish · GET/POST /chat/sessions · DELETE /chat/sessions/{id} · POST /chat/stream · POST /chat/stop · POST /interactions/{id}/resolve · POST /sessions/{id}/actions · POST /sessions/{id}/actions/import · GET /sessions/{id}/actions/pending · POST /actions/{id}/confirm

**intelligence_v2（29，前缀 /api/v2）**：GET /events · GET /events/{id} · GET /repositories/trending · GET /entities/{key} · GET /admin/events · POST /admin/events/reanalyze · GET /admin/events/{id} · POST /admin/events/{id}/analyze · POST /admin/events/{id}/publish · POST /admin/events/{source_id}/merge · POST /admin/events/{id}/split · PATCH /admin/events/{id} · POST /admin/events/{id}/rescore · GET /admin/sources · POST /admin/sources · POST /admin/sources/preview · GET /admin/coverage · GET+POST /admin/coverage/recall-benchmark · GET /admin/audit · GET /admin/email-deliveries · PATCH /admin/sources/{key}/enabled · PATCH /admin/sources/{key} · PATCH /admin/sources/{key}/schedule · POST /admin/sources/{key}/test · POST /admin/sources/{key}/run · GET+POST /admin/candidates · POST /admin/candidates/{id}/approve · POST /admin/candidates/{id}/ignore · GET+POST /admin/prompts · POST /admin/prompts/{id}/publish · POST /admin/prompts/{id}/rollback

（模块小计与 §0 的 169 端点对应；个别模块用动态路由参数计数可能 ±1。）

### 4.3 服务模块分域（57 个）

**采集域（crawlers + 源服务）**：github_crawler（趋势+仓库元数据+中文速读支持）· baidu_crawler · crawlers/__init__ run_daily_crawl（行业与厂商动态）· aliyun_solution_service（阿里云+华为云方案目录）· competitor_news_service（友商动态）· community_insight_service（知乎/CSDN/腾讯/百度社区）· agent_launch_service（AI 应用官方动态）· ai_app_sources（应用源清单）· source_registry_service（intelligence_sources 注册表 CRUD）

**发现域（Discovery）**：discovery_service（RSS/arXiv/HN/HF/ProductHunt/GitHub Search/api_json/html_links 适配器抓取→候选池）· ai_relevant 过滤（_matches_topics 主题关键词）· 候选 approve/ignore

**事件与情报加工域**：event_service（事件 CRUD/合并/拆分/重评分/发布）· event_reanalysis_service · intelligence_data_service（store_* 系列落库适配）· intelligence_format · intelligence_decision_service · entity_service（实体页）· repository_service（趋势仓库）· scoring_service · hotspot_service · radar_service（雷达+事件 AI 分析）· evaluation_service（业务价值评估+中文速读翻译）· daily_board_insight_service（六板块洞察）· daily_ai_brief_service（每日简讯+版本+邮件追踪）

**数据分析与呈现域**：insight_dashboard_service · insight_agent_runtime（业务 Agent：提示词+SSE）· research_service · context_service（Agent 上下文组装）· knowledge_service（RAG）· data_semantics · insight_format

**Agent 域**：agent_service（会话/工件/动作）· agent_audit_service · agent_task_service · agent_sso_service · agent_runtime_service（→runtime-manager.mjs 桥）· embedded_agent_service（每回合一个 Hermes 进程）· hermes_core_worker（NDJSON stdin/stdout 协议）· insight_agent_runtime（业务 Agent）

**邮件域**：email_service（订阅/发送/快照/送达尝试）· email_dashboard · email_technical_dashboard

**运维与治理域**：system_health_service · freshness_service · maintenance_service · chain_inspection_service（链路巡检）· recall_benchmark_service（召回基准）· startup_service · runtime_config_service · embedding_config_service · prompt_service（提示词版本管理）· ai_usage_service（AI 用量记账）· metric_service · admin_overview_service · page_snapshot_service · source_image · workbench_service · pipeline_service（三域流水线编排）· table_export_service · raw_evidence_service

### 4.4 两个爬虫模块

- `github_crawler.py`：refresh_and_store 主入口（08:00 任务调用）；含仓库元数据抓取与业务评估的数据准备
- `baidu_crawler.py` + `crawlers/__init__.py`：百度热搜与行业厂商动态日爬

---

## §5 数据层

### 5.1 连接拓扑

```
backend (psycopg2)
  ├─ DIRECT_URL  → supabase-db:5432 直连（DDL / Alembic / schema 操作优先）
  └─ DATABASE_URL → supabase-pooler:5432 会话池（业务读写，supavisor 2.9.13）

frontend (浏览器 Supabase JS)
  └─ /supabase/* rewrite → supabase-envoy:8000 → gotrue(认证 JWT) / postgrest / realtime / storage

alembic 迁移（backend/migrations/versions, 38 个）
  执行入口与各迁移职责见 §10.3 版本治理与 alembic_history；DDL 全部经 DIRECT_URL
```

### 5.2 Alembic 迁移史（38 个，按拓扑时间线归并）

**初始与基础（6）**：beb54db85b7f initial_schema_stamp（SQLite→PG 奠基）· a7b8c9d0e1f2 board_daily_insights · d4e5f6a7b8c9 platform_task_runs · b7c8d9e0f1a2 intelligence_data_foundation · c3d4e5f6a7b8 daily_homepage_recommendation · a1b2c3d4e5f6 email_subscriber_language

**评估与业务化（7）**：a9b0c1d2e3f4 repository_business_prompt 种子 · c1d2e3f4a5b6 repository_technical_assessment_prompt · 8c4d5e6f7a8b chinese_project_briefs · 922ac3fa2764 vendor_names_to_english · f6a7b8c9d0e1 link_project_analysis · e3f4a5b6c7d8 event_business_targets · d2e3f4a5b6c7 labeled_hotspot_recall_benchmark

**源治理（8）**：a0b1c2d3e4f5 expand_intelligence_sources · f9a0b1c2d3e4 morning_source_schedules · f5a6b7c8d9e0 register_source_task_contract · b0c1d2e3f4a5 merge_source_task_and_prompt_heads · f4a5b6c7d8e9 use_registry_community_urls · e1f2a3b4c5d6 connect_product_hunt_discovery · f2a3b4c5d6e7 github_search_discovery · f3a4b5c6d7e8 track_ai_application_source_freshness

**事件与发现（7）**：d9e0f1a2b3c4 discovery_candidates_and_prompts · e7f8a9b0c1d2 review_new_events · c8d9e0f1a2b3 event_merge_link · a1c2e3f4b5d6 event_analysis_freshness · a2c3e4f5b6d7 pipeline_run_counts · e5f6a7b8c9d0 cache_source_analysis · d6e7f8a9b0c1 raw_content_versions

**每日简报与邮件（6）**：b4c5d6e7f8a0 daily_ai_brief_versions · c5d6e7f8a9b0 daily_ai_brief_email_trace · e0f1a2b3c4d5 email_delivery_attempts · e4f5a6b7c8d9 email_snapshots · f8a9b0c1d2e3 email_subscriptions_page_snapshots · a5c6e7f8b9d0 chain_inspections

**遗留迁移（1）**：a4c5e6f7b8d9 legacy_competitor_events（配 backfill 脚本）

### 5.3 核心数据域（按消费端点反推）

| 域 | 代表表（推测，按服务层 SQL 归纳） | 主要写入方 | 主要读取方 |
|---|---|---|---|
| 趋势仓库 | trending 表族 + 仓库业务评估/中文速读 | github_crawler · evaluation_service | /github-trending/* · /v2/repositories/trending · technology 页 |
| 事件流 | events + evidence + merge_link + business_targets | discovery→event_service 分析流水 | /v2/events* · admin/events · events/[id] 页 |
| 源注册表 | intelligence_sources + source_topics | source_registry_service | admin/sources · 调度注册 |
| 社区/友商/应用 | community_* · competitor_news* · ai_applications | 各采集服务 | 各 insights 页 + 快照路径 |
| 方案目录 | solution catalogs（aliyun/huawei） | aliyun_solution_service | /solutions/* · solutions 页 |
| 工作台 | requirements · workbench solutions | workbench_service | /workbench/* 页 |
| Agent | agent sessions/artifacts/actions/interactions/audit | agent_service | /agent/* 端点 |
| 邮件 | subscribers · subscriptions · snapshots · delivery_attempts | email_service | /email/* 端点 |
| 快照 | page_snapshots（唯一快照真源） | page_snapshot_service | 读路径中间件 + /api/pages/*/latest |
| 任务与流水线 | task_runs · pipeline_runs · chain_inspections | task_service · pipeline_service | admin/tasks · admin/pipelines |
| 知识 RAG | 向量列 + chunk 表（knowledge_service 管理） | knowledge_service:sync_public_knowledge | /agent/knowledge/* · 深度检索 |
| 运维 | ai_usage · metrics · runtime_config · embedding_config | 对应治理服务 | admin/llm · admin/runtime · readiness |

---

## §6 数据管道与调度

### 6.1 16 个定时任务（APScheduler, Asia/Shanghai, 后端进程内）

| key | 名称 | 时间 | 目标 | AI |
|---|---|---|---|---|
| github_daily | GitHub 趋势采集 | 08:00 | crawlers.github_crawler:refresh_and_store | – |
| trending_business_eval_daily | 项目业务价值评估 | 08:20 | evaluation_service:evaluate_trending_business | ✓ |
| solution_catalogs_daily | 云厂商方案采集 | 08:10 | aliyun_solution_service:refresh_solution_catalogs | – |
| daily_crawl | 行业与厂商动态采集 | 08:15 | crawlers:run_daily_crawl | – |
| competitor_daily | 友商动态采集 | 08:25 | competitor_news_service:refresh_competitor_news | – |
| community_insights_daily | 社区热点采集 | 08:30 | community_insight_service:collect_daily | – |
| ai_applications_daily | AI 应用官方动态采集 | 08:35 | agent_launch_service:refresh_official_sources | – |
| discovery_sentinel_daily | Discovery Sentinel 候选发现 | 08:45 | discovery_service:discover_candidates | – |
| knowledge_sync_daily | 公共知识同步 | 08:50 | knowledge_service:sync_public_knowledge | ✓ |
| project_briefs_zh_daily | 项目中文速读 | 08:55 | evaluation_service:translate_project_summaries | ✓ |
| radar_event_analysis_daily | Radar 事件分析 | 09:05 | radar_service:analyze_radar_events | ✓ |
| board_insights_daily | 板块近期情报 | 09:20 | daily_board_insight_service:refresh_all | ✓ |
| daily_ai_brief | 每日 AI 洞察简讯 | 09:30 | daily_ai_brief_service:refresh | ✓ |
| page_snapshots_daily | 发布每日页面快照 | 09:50 | page_snapshot_service:publish_page_snapshots_sync | – |
| cleanup | 历史数据清理 | 03:00 | maintenance_service:cleanup_old_data | – |
| scheduled_email | 订阅邮件发送 | 每分钟 | email_service:send_scheduled_digests | – |

调度注册有两条额外机制：

1. **源级 cron 覆盖**：`load_source_schedules()` 读取 intelligence_sources 表中每个启用源的 schedule.cron，动态生成 CronTrigger 覆盖默认时间（同 key 合并注册，replace_existing）。
2. **daily_ai_brief 可暂停**：`daily_brief_schedule_enabled()` 为假时注册后立即 pause，改由 admin 页面手动触发/重发。

任务执行统一经 `run_task`：task_runs 记录、coalesce=True、max_instances=1、misfire_grace_time=6h。`recover_orphaned_runs` 在启动时把崩溃残留的 running 状态收敛为失败。

### 6.2 每日流水线时间线（默认时刻）

```
03:00 cleanup 历史清理
08:00 ┐
08:10 │ 采集浪涌：GitHub / 云方案 / 行业厂商 / 友商 / 社区 / AI 应用官方
08:15 │ （7 个采集任务，源级 cron 可改期）
08:25 │
08:30 │
08:35 ┘
08:20 业务评估(AI) → 08:45 Discovery Sentinel → 08:50 知识同步(AI)
08:55 中文速读(AI) → 09:05 Radar 事件分析(AI) → 09:20 板块洞察(AI)
09:30 每日简讯(AI) → 09:50 页面快照发布（读路径当日口径切换）
每分钟 scheduled_email 轮询订阅发送（含送达尝试记录）
```

三域流水线（pipeline_service）另外提供面向 admin 的手动编排：technology/solutions/community 等域按 pipeline_steps 顺序执行，支持 resume_from 断点续跑，过程与计数存 pipeline_runs。

### 6.3 源注册表与 17 类适配器

SOURCE_TASK_BY_ADAPTER 完整映射（适配器 → 归属采集任务）：

```
github_trending ──────────────┐
aliyun_solutions + huawei_solutions ─→ solution_catalogs_daily
competitor_news ──────────────┤
ai_applications_official ─────┤
product_hunt_feed + hacker_news_api + hugging_face_api + arxiv_api
github_search_api + rss_feed + api_json + html_links ────→ discovery_sentinel_daily
community_zhihu + community_baidu + community_tencent + community_csdn ─→ community_insights_daily
```

### 6.4 采集 → 落库 → 呈现的数据流（以 GitHub 趋势为例）

```
GitHub Trending 页
  → github_crawler.refresh_and_store
  → intelligence_data_service.store_github_signal（按 scrape_date+rank 落库）
  → [08:20] evaluation_service.evaluate_trending_business（AI 业务价值评估）
  → [08:55] translate_project_summaries（中文速读）
  → [09:50] page_snapshot_service 读取 /api/v2/repositories/trending 等端点
  → page_snapshots 当日行
  → 次日读路径回放（管理员登录后）
```

---

## §7 前端架构

### 7.1 构建与代理（next.config.ts + proxy.ts）

```
Next.js standalone（output: "standalone", 容器内 next-server）
rewrites:
  /api/*  → http://insight-backend:8000/api/*     (API_PROXY_TARGET)
  /supabase/* → http://supabase-envoy:8000/*      (SUPABASE_INTERNAL_URL)
proxy.ts（middleware 导出）：
  放行 /admin/login、/api/*、/supabase*、旧 auth 三页
  其余路由经 updateSession 取 Supabase 用户：
    admin 且未禁用 → 放行
    否则 → 302 /admin/login?next=<原路径>
```

### 7.2 页面树（44 页 + 4 顶层组件）

```
/                          首页（home，6 模块 + 推荐位）
/admin                     管理台首页
  ├─ dashboard · tasks · jobs · scheduler · operations · system
  ├─ sources · coverage · candidates · events · prompts
  ├─ emails · llm · runtime · knowledge · users · access · login
/auth/agent                Agent SSO 落地页（带 ticket 入口）
/dashboard                 旧版仪表盘
/events/[id]               事件详情
/history                   历史列表
/insight-agent             嵌入式 Agent 页面
/insights/hotspots         热点雷达
/insights/app-launches     AI 应用发布
/insights/community        社区洞察
/insights/competitors      友商动态
/insights/solutions        方案库（+ [id] 详情）
/knowledge                 知识检索
/reports                   研究报告
/repositories/[entity_key] 仓库/实体详情
/search                    搜索
/settings                  设置
/workbench                 工作台
  ├─ requirements（列表/new/[id]）
  ├─ solutions（列表/new/[id]）
  └─ ai                    AI 工作台
```

另有 error/loading/layout 顶层组件；`/admin` 下 19 个子页全部为管理域。

### 7.3 请求层分裂（当前前端断链的直接原因）

```
authenticatedFetch / optionalAuthenticatedFetch (lib/authenticated-fetch.ts)
  └─ 32 个文件已迁移：自动带 Supabase Bearer → 守卫放行 → 数据正常
普通 fetch（不带凭据）
  └─ page.tsx / daily-ai-brief.tsx / agent-launches.tsx 等核心数据页
     └─ admin_api_guard 401 → 页面空态（即当前症状）
```

### 7.4 组件与 lib

- **组件（components/）**：app-shell（全局壳）· auth-provider（Supabase 会话）· insight-page-shell / insight-dashboard / insight-card（情报页三件套）· agent-shell + insight-agent-shell（Agent 外壳）· daily-ai-brief · daily-board-insight · event-stream · agent-launches · search-bar · page-tracker（埋点）· background-fill-dialog · expandable-text · header-date · section-header · ui/（基础 UI 库）
- **lib（36 个模块）**：数据加工（intelligence/insight-dashboard/ai-app-intelligence/solution-intelligence/evaluation-sections/home-content/home-focus/background-fill/data-display/radar-markers/agent-events/agent-page-context/admin-task-status/ui-actions/vendor-image/workbench）· 基础设施（api/authenticated-fetch/use-safe-fetch/client-data-cache/preferences/utils/track）· 每个业务 lib 多配有同名 .test.ts（22 个测试文件）
- **utils/supabase/**：client · server · middleware · auth-cookie（4 件套，@supabase/ssr 会话管理）

### 7.5 全局智能助手（chat.js，挂 layout.tsx）

- 注入方式：`window.__CHAT_API_URL__` 注入实际后端地址（CLAUDE.md 规则约束点）
- 后端：POST /api/chat 与 /api/chat/stream（routers/chat.py，知识库与快捷问题需与主导航同步维护）
- 浮层 UI：固定右下角按钮 + 380×520 面板，内联样式注入

---

## §8 Agent 与 AI 体系

### 8.1 三个 Agent 面

| 面 | 入口 | 执行体 | 会话/数据 |
|---|---|---|---|
| ① 站点助手（小雷达） | 前端全局浮层 chat.js → /api/chat(/stream) | insight_agent_runtime（后端进程内，OpenAI 兼容调用） | chat 表 + 知识库 |
| ② 嵌入式 Insight-Agent | /insight-agent 页 + 32 页 context 注入 → /api/agent/* | embedded_agent_service：**每回合 fork 一个 Hermes Python 进程**（stdin/stdout NDJSON 协议，hermes_core_worker 为进程入口） | agent_service 的 sessions/artifacts/actions/interactions |
| ③ 独立 Hermes 空间 | :4096 网关（SSO）→ insight-hermes 容器 | Hermes v2026.8.19 主引擎 + runtime-manager.mjs | /srv/insight-agent 数据根 + 网关会话表 |

### 8.2 面② 进程模型（关键设计）

```
浏览器 SSE /api/agent/chat/stream
  → embedded_agent_service（active_turns 进程登记表；注释明确：单 API worker 架构，
    多 worker 前需共享路由——这是已知横向扩展约束）
  → Popen 启动 hermes_core_worker 子进程
     · stdin: 初始回合 → 后续 interaction 答复
     · stdout: 严格 NDJSON 事件流（emit() 带 stdout 锁）
     · ask_user() 回调 → interaction.request/resolved 事件 ⇄ 浏览器交互
     · sys.stdout 重定向 stderr 防上游污染协议
  → 工具目录经 config.yaml tools.tool_search=off 关闭（收窄能力面）
  → 进程结束即回合结束（stop() terminate + 5s 兜底）
```

### 8.3 面③ Hermes 空间（每用户独立）

- agent-spaces admin 端点可 start/stop 用户空间；首次访问自动创建
- 模型：deepseek-v4-flash-0731 经 OpenAI 兼容网关（HERMES 容器内 env）
- 限制：HERMES_MAX_ACTIVE=6 并发回合、HERMES_IDLE_SECONDS=1800 空闲回收、磁盘预算 20480MB
- 后端与 Runtime Manager 通信：X-Insight-Runtime-Secret 头（值同网关密钥）+ X-Insight-User-Id 等身份头

### 8.4 AI 调用统一层

- `ai_service`：全部聊天补全统一入口，chat_completions_url 规范化；运行时热切换（admin/llm 页 → runtime_config_service，改 CHAT_API_URL/KEY/MODEL 即时生效，不需重启）
- `embedding_config_service`：向量模型热切换（EMBEDDING_*）
- `ai_usage_service`：用量记账
- 外部依赖：聊天 LLM / Embedding API / Reranker API（settings 含 RERANKER_*，knowledge_service RAG 与 deep_searcher 深度检索使用）

### 8.5 RAG 与深度检索

```
knowledge_service（小型 RAG）
  chunk_text(1200/150 重叠) → embed()（外部 API）→ Postgres 向量列
  sync_public_knowledge（08:50 任务）+ admin reindex
deep_searcher_integration
  init_deep_searcher → retrieve_context(top_k) → context_to_str(6000 字符上限)
  deep_research(query, max_iter=3) 迭代式深度检索（chat 端点上下文增强用）
```

### 8.6 Insight-Agent 知识包（insight_agent_runtime）

打包随镜像的版本化文档（/app/agent_knowledge，源目录 services/insight-agent）：AGENTS.md · BUSINESS_CONTEXT.md · SOLUTION_ENGINEERING_WORKFLOW.md · ROLE_SOLUTION_ARCHITECT.md + plugins/。业务阶段映射 technology_research→Discover 等（solution_analysis/architecture/design/requirement_analysis…）。

---

## §9 邮件体系

```
订阅管理：/email/subscribe · /email/preference（自管退订页）· admin 端 /email/subscribers CRUD + 语言偏好
SMTP：默认取 settings.SMTP_*，可经 /email/smtp-config（GET/PUT + test）后台热配（email_dashboard）
发送：scheduled_email 每分钟轮询 → send_scheduled_digests（按订阅类型+语言分组）
追踪：e0f1a2b3c4d5 email_delivery_attempts（每次尝试记录）
      c5d6e7f8a9b0 daily_ai_brief_email_trace（简讯发送留痕）
      e4f5a6b7c8d9 email_snapshots（发送内容快照，GET /email/snapshots/{id} 可回看）
重发：POST /admin/daily-ai-brief/retry-email（admin/tasks 页）· POST /email/send-now 手动即时发
预览：GET /email/preview（渲染未发送视图）
```

---

## §10 运维体系

### 10.1 看门狗与部署

```
insight-docker-health-guard.timer（~5min）
  → docker-health-guard.sh
    → scripts/health-check.sh full（live + ready + business-eval 契约）
    → 失败时尝试数据新鲜度修复（freshness_service）
    → 仍失败 → CRITICAL 告警（当前因 §12-1 的 401 而持续误报）
旧 insight-health-guard.timer 并存

./scripts/deploy-docker.sh（标准发布流程）
  pytest → lint → compose build → systemd 切换 → health-check 循环 → 镜像清理
./scripts/health-check.sh full：三段检查，business-eval 段当前 401 失败
./scripts/diagnose_core.py · snapshot_evidence.py（诊断与证据快照）
./scripts/check-version.py（版本一致性校验，见 §12-3）
./scripts/install-docker-compose.sh · deploy.sh（旧路径）
```

### 10.2 版本治理现状（详见 §11-§12）

compose 镜像已切 `1.1.5-rc.2`，而 `frontend/package.json` 仍为 `1.1.5-rc.1`、后端 settings 默认值 rc.1、README 未同步——`check-version.py` 在当前工作区必然报不一致。

### 10.3 alembic 执行与 schema 治理

- 运行时 DDL 开关 `STARTUP_SCHEMA_ENABLED=false`（当前）：启动不做 schema 变更，迁移须显式执行
- `REQUIREMENT_ABSORPTION_ON_STARTUP=true`：历史需求吸收（工作台需求入库）
- runtime schema（ensure_runtime_schema）与 Alembic 38 个版本并存；`page_snapshots` 等运行时表由 init_crawler_tables/startup_service 建立
- doc/supabase-local-governance-baseline-2026-10-28.md 为当日 Supabase 治理基线文档

---

## §11 版本与代码状态快照（2026-10-28）

| 项 | 值 |
|---|---|
| 最近 release 提交 | 4dead52 release: publish InsightPro v1.1.0 |
| 之后提交 | aa1351a fix: patch frontend dependency vulnerabilities（+30/−21，10 文件） |
| Git tag 最新 | v1.1.1（对应 aa1351a） |
| 工作区未提交（跟踪文件） | 68 文件 +1907/−670 |
| 工作区未跟踪新文件 | 67 个，其中约 23 个代码文件 +1529 行（其余 40 个为 .playwright-mcp 截图/日志） |
| 相对 v1.1.0 总改动 | ≈90 代码文件，净 +2700 行（总变更 ≈3400 行，全仓 ≈3.4 万行，约 10%） |
| 运行镜像 | insight-web-backend/frontend:1.1.5-rc.2（compose 引用） |
| frontend/package.json | 1.1.5-rc.1（漂移） |
| backend settings APP_VERSION 默认 | 1.1.5-rc.1（漂移） |
| 容器启动时间 | 当日 07:51；16:01 曾向容器热补丁代码但未重启进程（见 §12-2） |

未提交改动按域分布（vs v1.1.0，numstat）：

| 域 | 文件 | 行 |
|---|---|---|
| backend/services | 10 改 + 5 新 | +260/−166 与 +新 service |
| backend/routers + auth 拆分 | 7 | +117/−47 |
| backend/tests | 12 改 + 4 新 | +124/−66 |
| backend/migrations | 6 新 | — |
| frontend/src | 27 改 + 4 新 | +131/−361（净删，旧 auth 四页删除） |
| AGENTS.md | 1 | +1178 |
| compose/配置 | 4 | +22/−6 |
| log/versions.md | 1 | +36/−1 |

---

## §12 已知问题与断点（按严重度）

1. **前端核心数据页全空（线上正在发生）**：`admin_api_guard`（main.py:146，未提交）对匿名 /api/* 一律 401；`page.tsx`、`daily-ai-brief.tsx`、`agent-launches.tsx` 等仍用普通 fetch 不带凭据 → 空态。32 个已迁 authenticatedFetch 的页面登录后正常。两条修复方向未定：前端补令牌 vs 后端对快照路径放开匿名读。
2. **容器代码与运行进程脱节**：rc.2 镜像当日 07:51 启动后，16:01 又向容器热补丁了 page_snapshot_service（内部密钥头修复），但 uvicorn 无 --reload 未重启 → 补丁未生效；09:50 与 16:38 两次快照发布曾 401 失败。快照表当日行是否为最新需以 page_snapshots.generated_at 核对。
3. **版本三元漂移**：compose=rc.2 / package.json=rc.1 / settings 默认=rc.1，check-version.py 必挂。
4. **`/api/pages/{page}/latest` 匿名 401**：不在白名单也不在 PATH_TO_PAGE 旁路，聚合快照接口对匿名同样断链。
5. **看门狗持续 CRITICAL**：health-check full 的 business-eval 段因 #1 而失败，每 ~5 分钟告警一次且无法自愈。
6. **旧 8999 端口 uvicorn 进程**：宿主上另有 `uvicorn backend.main:app --port 8999` 直跑进程（07:51 启动），疑似 insight-backend.service 遗留，与容器 8000 并存——确认无人依赖后应下线。
7. **Hermes 聊天 API key 明文 env**：`docker inspect insight-hermes` 可见 sk-… 密钥；建议改为文件挂载（网关密钥已是正确做法）。
8. **trending.db-wal/-shm 未被忽略**：backend/ 下 SQLite 残留 WAL 文件未进 .gitignore，出现在未跟踪列表中。
9. **AGENTS.md +1178 行未提交**：工程说明主体悬空在未跟踪区，需随下个候选版一并提交。
10. **单 worker Agent 约束**：embedded_agent_service 注释明确单 API worker 架构，横向扩容前需共享 active_turns 路由（技术债已显式标注）。

---

## 附录 A：配置字段全景（settings.py）

```
版本/地址   APP_VERSION · BASE_URL · PUBLIC_IP · CORS_ORIGINS
AI 聊天     CHAT_API_URL · CHAT_API_KEY · CHAT_MODEL （可被 runtime_config 覆盖）
向量/重排   EMBEDDING_API_URL/KEY/MODEL/DIMENSIONS · RERANKER_API_URL/KEY/MODEL
Agent       AGENT_RUNTIME_CONTROL_URL · HERMES_PUBLIC_URL · HERMES_SSO_SECRET · HERMES_COOKIE_SECURE
Supabase    SUPABASE_URL · SUPABASE_ANON_KEY · SUPABASE_SERVICE_KEY · DIRECT_URL · DATABASE_URL
邮件        SMTP_HOST/PORT/USER/PASSWORD · EMAIL_FROM · EMAIL_TO
启动开关    STARTUP_CATCHUP_ENABLED · SCHEDULER_ENABLED · REQUIREMENT_ABSORPTION_ON_STARTUP · STARTUP_SCHEMA_ENABLED
爬虫        CRAWLER_TIMEOUT · CRAWLER_RETRY · CRAWLER_RETRY_DELAY
```

## 附录 B：术语表

| 术语 | 含义 |
|---|---|
| 快照口径 | 读路径只回放 page_snapshots 当日行、不实时查库的对外数据口径 |
| PATH_TO_PAGE | 30 条受快照机制保护的端点路径 → 所属页面映射 |
| internal-key | x-insight-internal-key 头，值=网关密钥，仅进程内快照发布使用 |
| 网关密钥 | /etc/insight-hermes/backend-gateway.secret，三用：nginx auth_request 校验、Agent Runtime 鉴权、进程内快照旁路 |
| Discovery Sentinel | 08:45 的候选发现任务，扫描 RSS/arXiv/HN/HF/PH/GH-Search 等源产出候选池 |
| 三域流水线 | pipeline_service 按 technology/solutions/community 等域的手动编排执行 |
| Hermes | 上游开源 Agent 引擎，本平台以「每回合一进程」与「每用户一空间」两种方式复用 |
| rc 版本 | 1.x.0-rc.N 候选版；正式发布需五处同步（package.json/锁文件/后端默认/compose/README） |

---

*生成方式：本文全部内容来自 2026-10-28 对工作区代码、运行容器、systemd 单元与 git 状态的直接枚举与交叉核对；未引用任何未经验证的二手资料。改动统计基线为 v1.1.0（4dead52）。*
