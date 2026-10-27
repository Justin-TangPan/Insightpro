# InsightPro 数据体系审视

> 本文是 2026-10-27 发布部署前的只读审计快照，其中数据库版本、来源数量及风险项描述的是当时观察到的运行状态。1.1.0 发布已执行应用迁移并通过完整健康检查；需要判断当前数据库或风险状态时，应重新核查运行环境，不能直接把快照结论当成现状。

> **状态更新（2026-10-23）**：以下主体是初始审计快照，不能直接代表当前部署。后续 V2 实施已推进迁移及 Source 管理。截至本次只读核验，生产库 Alembic head 为 `c1d2e3f4a5b6`，V2 核心表和 Prompt 版本列均已存在，`intelligence_sources` 有 10 条记录。因此第 5、9、10 节中“候选表缺失、schedule 缺 task_key、数据库落后”的判断已过期；不据此对线上迁移或修改数据。首页与部分业务/邮件读路径仍有 V1/V2 并行，需继续按实施验收记录推进。

审视日期：2026-10-23。范围：当前工作区代码、迁移文件、Postgres 只读元数据；没有修改代码、表结构或业务数据。**代码行为**与**当前数据库状态**分开描述。数据库连通不等于当前工作区代码已部署；未调用运行中的 API，也未读取业务记录内容。`pg_class` 行数属于统计估算，不作为重复或缺失记录的证据。工作区原有大量未提交改动，本报告依据其当前状态。

## 1. 当前数据架构

- 主库是 Supabase Postgres，连接由 [`backend/db.py`](backend/db.py#L24-L53) 的 `DIRECT_URL` / `DATABASE_URL` 提供。当前只读检查见 40 张 `public` 基础表；`backend/trending.db` 属历史 SQLite 迁移来源，不是当前主库。[`backend/db.py`](backend/db.py#L4-L11)
- 旧业务表包括 `github_trending`、`trending_business_eval`、`competitor_news`、`cloud_vendor_news`、`aliyun_solutions`、`vendor_ai_applications`、`email_subscribers`、`knowledge_chunks` 等；旧域表有 ORM Model，V2 情报表主要由 Alembic 与原生 SQL 定义。[`backend/models`](backend/models) · [`V2 基础迁移`](backend/migrations/versions/b7c8d9e0f1a2_intelligence_data_foundation.py#L12-L108)
- V2 主链为 `intelligence_sources` → `intelligence_raw_items` → `intelligence_event_evidence` → `intelligence_events` / `intelligence_entities` / `intelligence_metric_snapshots`；分析另存 `intelligence_analysis`、`board_daily_insights`。启动流程会执行 Alembic，并另建知识索引、官方应用和板块分析表。[`backend/services/startup_service.py`](backend/services/startup_service.py#L15-L92)
- API 进程内的 APScheduler 注册静态 `TASKS`；源注册表的 `schedule` 不是调度器配置来源。另有页面请求时采集、启动补采和内存缓存。[`backend/main.py`](backend/main.py#L24-L66) · [`backend/services/task_service.py`](backend/services/task_service.py#L32-L45)

## 2. 完整数据流

| Source → Collect | Store → Process → AI | API → UI / Email |
| --- | --- | --- |
| GitHub Trending → `github_daily`，热点页 GET 也可实时抓取 | `github_trending` + V2 raw/event/metric → `trending_business_eval`、中文速读、知识向量索引 | `/github-trending*` → 热点页；`/radar/intelligence` → 首页；技术邮件直接读最新 daily 快照 [`采集`](backend/crawlers/github_crawler.py#L51-L57) [`页面 GET`](backend/routers/hotspots.py#L64-L98) [`技术邮件`](backend/services/email_technical_dashboard.py#L9-L45) |
| 阿里云、华为云方案目录 → `solution_catalogs_daily` | `aliyun_solutions` + V2 raw/event → 板块日分析、知识索引 | 方案页、首页雷达、商业邮件 [`任务`](backend/services/task_service.py#L34-L42) [`索引`](backend/services/knowledge_service.py#L100-L122) |
| 五家云厂商动态 → `daily_crawl` 与 `competitor_daily` | `competitor_news`、`cloud_vendor_news`，部分写 V2 raw/event 与 `intelligence_analysis` | 厂商页、首页雷达、商业邮件 [`两个任务`](backend/services/task_service.py#L35-L36) [`写入`](backend/services/competitor_news_service.py#L105-L130) |
| 官方 AI 应用源 → `ai_applications_daily` | `vendor_ai_applications`；已核实项目还写 V2 raw/event；分析保存在应用字段 | 应用页、首页雷达、商业邮件 [`采集`](backend/services/agent_launch_service.py#L645-L695) [`应用 API`](backend/routers/hotspots.py#L18-L28) |
| 知乎、百度、腾讯云社区、CSDN → 请求时抓取 | 进程内 900 秒缓存 + V2 raw；板块日分析 | 社区页、首页雷达、商业邮件 [`backend/services/community_insight_service.py`](backend/services/community_insight_service.py#L83-L113) |
| Hacker News、Hugging Face、arXiv → `discovery_sentinel_daily` | V2 raw → 候选发现与人工审批 → V2 event/evidence | 管理后台候选、事件页；当前数据库缺少候选表，见 P1 [`backend/services/discovery_service.py`](backend/services/discovery_service.py#L58-L90) |
| 各板块来源 → `board_insights_daily` 10:00 | `board_daily_insights`，按来源指纹和 Prompt 版本尝试复用 | `/boards/{board}/daily-insight`、商业邮件读取当天缓存 [`backend/services/daily_board_insight_service.py`](backend/services/daily_board_insight_service.py#L131-L150) [`backend/services/email_dashboard.py`](backend/services/email_dashboard.py#L20-L58) |

商业邮件取当天板块缓存并实时读取雷达；技术邮件只读 `github_trending` 与评估表，另算趋势标签。首页实际调用 `/api/radar/intelligence`；五个业务页各有独立接口，V2 事件主要由事件详情和管理页直接使用。[`首页`](frontend/src/app/page.tsx#L42) · [`雷达`](backend/services/radar_service.py#L344-L410) · [`技术邮件`](backend/services/email_technical_dashboard.py#L9-L45)

## 3. 核心模型与关系

| 模型 / 表 | 标识与关系 | 审视结论 |
| --- | --- | --- |
| `intelligence_sources`、`intelligence_raw_items` | `source_key` → 原始项；原始项按 `(source_key, external_id)` 去重 | 可记录来源，但注册不等于接入任务。[`迁移`](backend/migrations/versions/b7c8d9e0f1a2_intelligence_data_foundation.py#L13-L56) |
| `intelligence_entities`、`intelligence_events`、`intelligence_event_evidence`、`intelligence_metric_snapshots` | `entity_key` 与事件键；证据桥表连接 event 和 raw，指标带 `raw_item_id` | V2 有证据链；首页还混入旧表和实时社区项，不能保证每张卡都以 V2 event 为主键。[`迁移`](backend/migrations/versions/b7c8d9e0f1a2_intelligence_data_foundation.py#L35-L96) [`雷达合并`](backend/services/radar_service.py#L414-L486) |
| `trending_business_eval`、`intelligence_analysis`、`board_daily_insights`、`homepage_daily_recommendations` | 分别按项目/日期、`(kind,source_key)`、板块/日期、日期存 AI 结果 | 多种粒度并存；`intelligence_analysis.source_key` 为多态文本而非原始项外键，应用分析可用 URL 作键，追溯需靠约定。[`分析表迁移`](backend/migrations/versions/e5f6a7b8c9d0_cache_source_analysis.py#L12-L20) [`应用分析`](backend/services/agent_launch_service.py#L460-L473) |
| `knowledge_chunks` | `(source_type,source_id,chunk_index)` 唯一 | 搜索索引是派生副本，源删除时没有统一的同步清理。[`backend/services/knowledge_service.py`](backend/services/knowledge_service.py#L47-L85) |

时间字段口径并不统一：旧 GitHub 用文本 `scrape_date/scrape_time`，厂商新闻另有 `published_date`，V2 用 `published_at/observed_at/event_at`；雷达部分路径携带 `date_basis`，旧源路径仍会用采集时间替代发布日期。社区源多无原文发布时间，只能作为观察时间。[`Models`](backend/models/competitors.py#L10-L34) · [`V2 迁移`](backend/migrations/versions/b7c8d9e0f1a2_intelligence_data_foundation.py#L45-L72) · [`雷达`](backend/services/radar_service.py#L344-L385)

## 4. 数据源与下游消费者

V2 迁移定义 13 个源键：`github_trending`、`product_hunt`、四个 `community_*`、`aliyun_solutions`、`huawei_solutions`、`ai_app_official`、`competitor_news`、`hacker_news`、`hugging_face`、`arxiv_ai`。[`种子定义`](backend/migrations/versions/b7c8d9e0f1a2_intelligence_data_foundation.py#L109-L125) 当前实库只读检查有 **9 条** `intelligence_sources` 记录，说明种子定义与实库现状不能视为相同清单；上述是代码计划覆盖范围，实际启用状态以实库为准。

| 来源组 | 直接消费 | 不会自动感知的环节 |
| --- | --- | --- |
| GitHub | 热点、雷达、搜索、技术邮件、知识索引、板块分析 | 新的同类源不会自动加入静态任务、搜索 SQL 或技术邮件。 [`任务`](backend/services/task_service.py#L32-L45) [`搜索`](backend/routers/search.py#L55-L90) |
| 方案目录 | 方案页、雷达、搜索、商业邮件、索引 | 目录源扩展需检查采集器、SQL、索引。 [`索引`](backend/services/knowledge_service.py#L100-L122) |
| 厂商动态 | 厂商页、雷达、搜索、商业邮件 | 厂商画像名单及字段写死，新增厂商不会自动进入画像。 [`backend/routers/competitors.py`](backend/routers/competitors.py#L18-L61) |
| 官方应用 | 应用页、雷达、搜索、商业邮件 | 来源配置在应用代码，新增源需改采集配置及映射。 [`backend/services/ai_app_sources.py`](backend/services/ai_app_sources.py) |
| 社区 / 发现源 | 社区页、雷达、候选管理、商业邮件 | 社区 FEEDS 固定；候选需迁移表及审批，不会自动变成所有业务页的数据。 [`社区 FEEDS`](backend/services/community_insight_service.py#L83-L112) [`候选`](backend/services/discovery_service.py#L58-L90) |
| Product Hunt | 注册表记录、未被调用的 feed 解析函数 | 代码中未找到解析函数调用方或对应定时任务；不能算当前已采集来源。 [`解析函数`](backend/services/radar_service.py#L60-L99) [`任务清单`](backend/services/task_service.py#L32-L45) |

## 5. 当前主要数据问题

| 等级 | 已确认事实及影响 | 证据 / 验证边界 |
| --- | --- | --- |
| **P0：无已证实项** | 未验证到数据丢失或线上整体不可用。 | 本次未调用线上 API。 |
| **P1 · 代码与实库版本差异** | 实库 `alembic_version=c8d9e0f1a2b3`；后续迁移 `d9e0f1a2b3c4` 所建的候选/Prompt 表、两张分析表的 `prompt_name/prompt_version` 列均缺失。当前工作区的板块分析与雷达会查询缺失列，Prompt 管理会查询缺失表。启动时会自动执行 Alembic，故这是**已确认结构差异**，不是已证实的线上请求故障。 | [`迁移`](backend/migrations/versions/d9e0f1a2b3c4_discovery_candidates_and_prompts.py#L12-L59) [`板块查询`](backend/services/daily_board_insight_service.py#L143-L150) [`雷达查询`](backend/services/radar_service.py#L284-L299) [`启动迁移`](backend/services/startup_service.py#L22-L30)；只读 `alembic_version` / `information_schema`。 |
| **P1 · 管理数据源控制失效** | 实库 9 条源的 `schedule` 都没有 `task_key`；启用和单源手动运行 API 都以该键查 `TASK_BY_KEY`，会拒绝这些记录。新增来源也不会自动生成 collector 或调度任务。 | [`backend/routers/intelligence_v2.py`](backend/routers/intelligence_v2.py#L121-L159) [`静态任务`](backend/services/task_service.py#L32-L46)；只读检查 9 条 `schedule`。 |
| **P1 · AI 结果可能落后于来源** | 官方应用采集冲突更新了 `source_text/published_at`，没有把已完成 `analysis_status` 改回 pending；后续分析只选 pending。来源变更后应用页可能继续显示旧分析。 | [`backend/services/agent_launch_service.py`](backend/services/agent_launch_service.py#L645-L695)；尚未按记录核实发生次数。 |
| **P1 · 首页/板块/邮件版本分叉** | 首页雷达读 V2 + 旧表 + 实时社区并在请求时合并、补 AI；业务页各读独立接口。商业邮件把当天缓存 AI 与实时雷达拼接，技术邮件独立查最新 GitHub 快照；缓存与页面无共享快照版本校验。 | [`雷达`](backend/services/radar_service.py#L344-L410) [`商业邮件`](backend/services/email_dashboard.py#L20-L58) [`技术邮件`](backend/services/email_technical_dashboard.py#L9-L45)；实际内容差异需抽样比对。 |
| **P2 · 源调度信息失真、重复抓取** | 四个社区源的种子写“15 分钟 / daily_crawl”，但 `daily_crawl` 只抓云厂商，社区按请求获取并缓存 900 秒。09:00 `daily_crawl` 与 09:02 `competitor_daily` 都抓同一云厂商列表并重写当天 `competitor_news`；热点页 GET 也会抓 GitHub，虽有冲突去重，仍可能与定时快照时间不同。 | [`种子`](backend/migrations/versions/b7c8d9e0f1a2_intelligence_data_foundation.py#L113-L121) [`采集`](backend/crawlers/__init__.py#L287-L320) [`厂商任务`](backend/services/competitor_news_service.py#L105-L125) [`热点 GET`](backend/routers/hotspots.py#L64-L98) |
| **P2 · 派生数据缺少失效链** | 知识索引每日 09:05 只 upsert 当前 GitHub/方案/已发布 artifact；未针对消失源清理旧文档。板块任务 10:00 只等待尚在运行的采集任务，不核对各源成功，可能根据旧源生成当天摘要。 | [`知识索引`](backend/services/knowledge_service.py#L47-L85) [`同步集合`](backend/services/knowledge_service.py#L100-L122) [`板块等待`](backend/services/daily_board_insight_service.py#L113-L128)；实库残留数量未核实。 |
| **P2 · 身份、时间与分类未统一** | V2 实体使用不同的 URL/名称键，雷达又按标准化 URL 或厂商加标题临时合并；厂商别名和类型关键词写在雷达中，厂商画像另有固定名单。不同 URL、别名或标题可产生分裂/误合并；来源发布时间与采集时间被多个查询混用。 | [`V2 写入`](backend/services/intelligence_data_service.py#L25-L68) [`雷达分类与合并`](backend/services/radar_service.py#L211-L240) [`雷达合并`](backend/services/radar_service.py#L414-L486) [`板块日期`](backend/services/daily_board_insight_service.py#L28-L43)；重复实体/标签数量未核实。 |
| **P3 · 多套分析结构与保留路由** | `trending_business_eval`、`intelligence_analysis`、板块缓存、首页推荐缓存分别存分析；`/homepage/recommendation`、`/homepage/modules`、`/radar/snapshot` 仍有实现，但仓库前端未找到调用。不能据此删除或称其无外部消费者。 | [`backend/routers/dashboard.py`](backend/routers/dashboard.py#L15-L117) [`业务邮件`](backend/services/email_dashboard.py#L20-L58) |

## 6. 数据同步与一致性风险

最短的失配链是：**源数据更新 → 旧业务表与 V2 双写/读取时间不同 → 板块 AI 缓存、雷达现场合并、业务页独立查询 → 商业邮件复用当日缓存**。另有官方应用的旧分析状态和知识索引的失效缺口。表中 P1/P2 项给出了各段证据；目前只证明链路允许不一致，未对具体业务记录做交叉抽样。

## 7. 重复、冲突与待判废弃结构

`competitor_news` 与 `cloud_vendor_news`、旧业务表与 V2 raw/event、四类 AI 结果是并行模型；它们的粒度和用途不同，**不能仅凭表名认定重复表或可删除**。`daily_crawl` / `competitor_daily` 的采集目标有真实重叠；Product Hunt 解析代码无调用；三个保留路由仅能确认仓库前端无调用。重复行、孤立行、外部消费者和废弃判定留待只读数据与访问日志核实。[`厂商采集`](backend/crawlers/__init__.py#L287-L320) · [`雷达`](backend/services/radar_service.py#L344-L410) · [`保留路由`](backend/routers/dashboard.py#L15-L117)

## 8. 数据治理缺失项

1. **统一来源契约与链路登记**：注册源、任务、采集器、业务页、搜索、邮件和索引没有一份可检查的映射；管理覆盖率的适配器支持名单也写在代码里。[`backend/routers/intelligence_v2.py`](backend/routers/intelligence_v2.py#L89-L108)
2. **派生结果的版本与失效规则**：需要为源记录、AI 结果、板块摘要、邮件与知识索引记录同一批次/来源指纹，定义来源更新、禁用、删除后的失效路径。
3. **统一实体与分类词表**：厂商/项目/产品别名、分类、标签目前分散在采集器、雷达和业务模块；没有可核对的规范键和同义词治理流程。
4. **时间与证据口径**：明确 `published`、`observed`、`updated`、`analyzed` 的字段与展示规则；要求每个可传播的 AI 结论可回指原始 URL/raw item。当前 V2 事件有证据桥表，但旧缓存和邮件并非都保存这种关联。
5. **运行态质量指标**：需要对源任务成功率、源→raw→event 覆盖、无证据事件、索引残留、缓存年龄、跨页面/邮件同批次一致性做只读巡检；本次仅确认结构和代码风险，不能量化历史脏数据。

## 9. 风险等级

P0：无已证实项。P1：实库与工作区代码版本差异、管理数据源控制失效、AI 应用分析可能陈旧、首页/板块/邮件取数分叉。P2：调度描述失真与重复采集、派生索引/摘要失效缺口、身份/时间/分类口径。P3：并行分析结构与仓库前端未调用的保留路由。具体证据与验证边界见第 5 节。

## 10. 下一阶段优先事项

1. **先确认部署版本与迁移状态**：核实运行进程代码版本、启动迁移日志及当前 DB head；在授权实施阶段处理迁移差异，再验证雷达、板块和 Prompt/候选接口。
2. **修正源注册契约**：先核对 9 条实库源的 `schedule`、任务映射与 UI 行为，再决定如何使启用、手动运行及新增源可追踪；不要把种子配置当成现网数据。
3. **建立源更新的下游清单与同批次校验**：优先覆盖 AI 应用分析、商业邮件、知识索引及首页/五业务页；抽样比对同一原始 URL 在各消费者中的时间、状态和分析版本。
4. **做只读质量基线**：统计重复 URL/实体/标签、孤立 raw/event、无原始 URL 的分析、索引残留和旧路由实际调用量；确认后再设计治理与迁移方案。

**QA 复查**：独立核对了实库版本/缺失列、9 条源配置、Product Hunt 调用链及 GitHub 入库去重。已将“接口故障”“重复行”“旧路由废弃”等未经运行证实的说法改成可验证的结构差异或风险。本阶段未执行修复、迁移、邮件发送或写入查询。
