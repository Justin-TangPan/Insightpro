# Insight-Pro V2 实施与验收记录

历史实施记录更新日期：2026-10-23

> **1.1.0 状态（2026-10-27）**：本文件早期 Current Architecture、Gap Analysis 和剩余迁移清单是当时的阶段快照，不能作为当前未完成事项清单。1.1.0 已增加事件审核运营、分业务 Pipeline、每日 AI 洞察简讯、邮件/页面快照及管理页面；前后端部署和完整健康检查通过。版本变更与验证详见[版本记录](../log/versions.md)。

## Current Architecture

- 现有采集器继续运行：GitHub Trending、社区热榜、云方案目录、官方 AI 应用和友商动态；任务中心继续使用现有 APScheduler 与 `platform_task_runs`。
- 新增 Hacker News、Hugging Face 与 arXiv 公共 API 发现采集，由 Discovery Sentinel 保存原始条目与可用指标；Discovery Candidate 需人工审核后才升级为 Event。
- V2 数据落在 PostgreSQL：`intelligence_sources` 管 Source Registry，`intelligence_raw_items` 保留来源原文/指标，`intelligence_entities` 统一实体，`intelligence_events` 聚合业务事件，Evidence 连接 Event 与 RawItem，MetricSnapshot 保存时序数据。
- GitHub、社区、方案、AI 应用和友商采集逐步写入 V2；历史兼容读取仍保留。Radar 优先读取 V2 Event 并关联来源证据，首页可进入 Event Detail。旧 API 与旧业务表不删除。
- 评分通过真实指标计算，趋势从 MetricSnapshot 生成；AI 分析使用输入证据，不承担生成指标事实的职责。Prompt Registry 支持 Draft、发布、版本和回滚；分析记录保存 Prompt 版本。
- 邮件订阅调度独立发送商业洞察和技术项目洞察两封邮件。前者来自现有五业务摘要，后者结合 GitHub 趋势和已有技术评估。
- 管理端新增来源、候选、事件、Prompt、覆盖与审计入口；后台接口统一位于 `/api/v2/`，并沿用现有 Admin 权限、任务调度和数据库。

## 已完成

- 增量 Schema Migration：Source、RawItem、Entity、Event、Evidence、MetricSnapshot、Audit、Candidate、Prompt Registry；保留 V1 表与字段。
- Source 健康记录、启停和按 Registry 任务键触发手动采集；Discovery Sentinel 已注册任务，可从 HN/HF 生成待审核 Candidate。
- GitHub 指标历史、基础趋势区间、评分服务、V2 Event Detail、Radar 事件去重及证据链接。
- Event 修改、Merge、Split、Ignore、Archive、Re-score 服务和审计；Prompt 草稿、发布及回滚 API 与界面。
- 双邮件模板与预览；管理端 Coverage/Audit、Sources、Candidates、Events、Prompts。
- V1 兼容读取、API V2 路由和 additive migration；未清理或覆写生产数据。

## Gap Analysis

| Requirement | Current | Gap | Solution / status | Priority | Risk |
|---|---|---|---|---|---|
| Source Registry / Adapter | 数据库 Registry 已种子化，部分现有采集器读取启停；HN/HF 已接入 | 已支持元数据编辑、启停、连接测试、共享任务 Cron 运行时更新和手动触发；尚不能创建可运行的新 Adapter Source | 新 Adapter 需先实现并注册 Collector，再开放相应 Source 配置 | P0 | 单独新增 Registry 行不会自动产生采集能力 |
| Discovery Sentinel | HN、HF 定时快照 + 未关联 RawItem 聚合 Candidate | 不是全网发现；Product Hunt、arXiv、Hugging Face Spaces 等未接入；跨标题实体归一有限 | 以新 Adapter 和 Entity Alias 扩展，Candidate 仍需人工审核 | P0 | 当前覆盖取决于少数基准源，不能承诺消除漏抓 |
| Hotspot Coverage Audit | 后台显示来源新鲜度、采集量、Candidate、基准清单和任务 | 目前是来源覆盖可观测性，尚未自动逐项抓取基准榜单并判定漏抓及原因 | 增加基准快照、实体匹配和漏抓原因工作流 | P0 | Coverage 数字不能等同于全市场召回率 |
| Event/Entity 历史回填 | 提供 GitHub backfill；新增采集写入 V2 | 其他旧业务表未完成全量历史映射；多个来源的语义级同事件聚合仍需 Alias/相似度规则 | 按业务分批回填，保持旧数据兼容 | P0 | 当前旧历史仍有部分只经 V1 Radar 拼装 |
| Metrics / Score | GitHub 与 HN/HF 保存部分历史值；趋势服务支持多个窗口 | HN/HF 指标还未进入每个实体的 Event Detail 展示；评论、下载等增长覆盖不完整；评分配置管理 UI 缺失 | 扩展指标映射并补评分版本管理 | P0/P1 | 不同来源的指标定义和采样间隔不同 |
| AI Analysis | 多个核心分析入口记录 Prompt Name/Version；无 Prompt 时沿用旧逻辑 | 并非所有 V1 分析器均使用 Prompt Registry；Analysis 记录尚未统一记录模型、证据 ID 和分析版本 | 逐个迁移剩余分析器，并统一分析元数据 | P0 | Prompt 更新后的缓存失效只覆盖已迁移的分析入口 |
| Email | 双邮件独立模板、预览、调度发送 | 邮件历史、逐收件人发送状态与管理员测试发送面板未完整建设 | 补邮件发送记录和管理端重发/预览工作流 | P0 | 实际投递取决于已有 SMTP 配置 |
| UI | 首页/Radar/业务页样式收敛、Event Detail、深浅主题沿用 | 社区、AI 应用、友商、解决方案近期事件和技术生态信号已读取 V2 Event；方案目录和 GitHub Trending 主列表仍为 V1；搜索已索引 V2 Event 并兼容未匹配的 V1；Repository Detail 缺专门路由 | 完整迁移剩余列表并继续保留历史兼容 | P0/P1 | 新旧数据并存期间不同页面时间范围可能不同 |
| Cache / Scheduler | 现有 Scheduler 和任务锁复用；日摘要按指纹缓存 | Source Schedule 尚未驱动实际调度；缓存依赖/TTL/失效尚未统一注册 | 接入共享数据版本/依赖失效机制 | P0 | Source 配置变更不会自动重排全部任务 |
| Monitoring / Audit | Source Health、任务错误、Coverage 与操作 Audit 页面 | Email/AI 分析粒度、异常告警/通知、审计筛选仍未统一 | 增加结构化运行记录、告警通道和过滤器 | P0 | 当前能定位任务和来源错误，但不能覆盖所有故障场景 |
| Permissions | V2 管理操作要求现有 Admin | Operator/Analyst/Viewer 分级未实现 | 扩展现有角色校验与最小权限矩阵 | P1 | 管理能力目前只向 Admin 开放 |

## Validation

- Backend：`pytest -q`，185 passed（最近一次完整运行）。
- Frontend：`npm run lint -- --no-cache`，0 errors、10 条现有 warnings；`npm run build` 成功。
- Migration：临时 PostgreSQL 从 V1 标记版本升级至 `d9e0f1a2b3c4`；验证 V2 Source 种子存在。生产数据库未执行迁移。
- Python：项目源码 `py_compile` 通过；`git diff --check` 通过。

## Deployment / Backfill Notes

先备份目标数据库，在维护窗口执行 `alembic upgrade head`，确认 Schema 后再运行 `python backend/backfill_intelligence.py`（按脚本参数与目标环境配置执行）。先验证新旧首页、Radar、邮件和任务中心，再逐步将业务页切到 V2。不要直接清理 V1 表。

不建议将本记录标记为全量 V2 验收完成：上表的 P0 差距需要在部署前或后续里程碑落实。

## Remediation Review — 2026-10-23

### Completed in this pass

- Solution Event key now includes the stable solution Entity key and change fingerprint, preventing different URLs with identical content from colliding.
- Coverage counts distinct active Events instead of joined Evidence rows.
- Admin Event listing can filter active, ignored, archived, or all statuses. Ignored and archived Events can be restored; active Events can be archived. Re-score is only shown for GitHub Events, the only supported adapter today.
- Admin Event operations now expose evidence IDs and support selecting evidence to split an active Event; merged Events remain read-only in the all-status view.
- Scheduled email delivery now records business and technical briefs independently, so retrying one failed brief does not resend its successful counterpart.
- Admin has an email delivery history view with per-recipient status, attempts, and latest error.
- Daily board analysis prefers V2 Event evidence, merges unmatched V1 rows during compatibility, and carries the selected `event_id` into the business email's Event Detail link.
- Radar reads load persisted analyses only. New analysis generation runs through a scheduled task capped at 24 events per run.
- Product Hunt is connected to Discovery Sentinel and eligible verified product listings can enter the review queue as single-source candidates.
- Source cron plans can be edited in the admin UI; sources sharing one collector task are updated together, and the running APScheduler job is rescheduled immediately.
- Community collector now writes RawItem → Entity → Event → Evidence; same normalized title from multiple community sources converges to one Event. Community UI reads V2 Events first and falls back to V1 only when no V2 events exist.

### Validation

- Full backend tests: 200 passed, 1 dependency deprecation warning.
- Frontend unit tests: 7 passed; Playwright desktop/mobile UI tests: 70 passed (isolated rerun).
- Frontend lint: 0 errors, 10 warnings; production build succeeded.
- Alembic offline SQL generation passed through `e1f2a3b4c5d6` (single head).
- `git diff --check`: passed.
- No database cleanup, production migration, or production-data backfill was performed.
- Running `next build` concurrently with Playwright initially stopped the shared dev server; rerunning UI tests separately passed. Playwright also reports an input `caret-color` hydration mismatch that does not fail current checks.

### Still open

- Source creation for new adapters; connection testing is implemented for currently registered URL-backed sources.
- Benchmark-backed hotspot recall coverage and broader discovery adapters.
- Complete Entity/Event/Evidence backfill and conversion of remaining business list views to shared Event IDs; daily summaries and business email now prefer V2 Events.
- Non-GitHub scoring and operational test coverage.
- Historical V1 data remains intact; compatibility reads and legacy tables have not been removed.

### Remediation Review — 2026-10-24

- Review found community ingestion stopped at RawItem, so the community Event API could not show newly collected topics. The write path now creates stable topic entities/events and links each source item as evidence.
- Community page now prioritizes V2 Event IDs, exposes source names/count, links to shared Event Detail, and retains the existing V1 endpoint as an empty-V2 compatibility fallback.
- Validation: backend 201 passed (one dependency deprecation warning); frontend build passed; frontend lint 0 errors / 10 warnings; frontend unit tests 7 passed; full desktop/mobile UI suite 70 passed, including the Event route assertion.
- Alembic offline generation reaches the single head `e1f2a3b4c5d6`; `git diff --check` passed. No database migration, cleanup, or production backfill was run.

Remaining V2-first UI migration covers AI applications, solutions, competitors, and technology ecosystem. Community is now migrated; those business views and repository detail remain open.

### Remediation Review — 2026-10-24 (continued)

- AI application updates now prefer the shared V2 Event list, with Entity vendor metadata, RawItem update kind and Event Detail links. Product catalog and registered source audit continue using their existing API; V1 update records remain the fallback when no V2 Event exists.
- Validation: backend 202 passed (one dependency deprecation warning); frontend build passed; lint 0 errors / 10 warnings; frontend unit tests 7 passed; full desktop/mobile UI suite 72 passed. The new AI application route was covered on both viewports.
- Migration SQL still generates to the single head `e1f2a3b4c5d6`; `git diff --check` passed. No production database or historical data was changed.

Remaining V2-first UI migration covers solutions, competitors, and technology ecosystem; search and Repository Detail also remain open.

### Remediation Review — 2026-10-24 (continued)

- Competitor updates now prefer the shared V2 Event API while retaining the existing vendor profile data, vendor/category filters and V1 fallback. List rows link to Event Detail; vendor and category are returned from Entity metadata and RawItem evidence.
- Validation: backend 202 passed (one dependency deprecation warning); frontend build passed; lint 0 errors / 10 warnings; frontend unit tests 7 passed; full desktop/mobile UI suite 74 passed, including community, AI application and competitor Event route tests.
- Alembic offline SQL generation remains at single head `e1f2a3b4c5d6`; `git diff --check` passed. No production migration, historical backfill, or data cleanup was run.

Remaining business UI migrations are the full solution catalog and full technology ecosystem list. Search and Repository Detail remain open.

### Remediation Review — 2026-10-24 (continued)

- Added a shared EventStream for the solutions and technology ecosystem pages. Solution change Events and recent cross-source technology Events now link to the canonical Event Detail; the existing solution directory and GitHub Trending/evaluation workflow remain available.
- Event list now returns vendor from Entity metadata or source RawItem content, plus categories/kinds and source names for business filtering and display.
- Validation: backend 202 passed (one dependency deprecation warning); frontend build passed; lint 0 errors / 10 warnings; frontend unit tests 7 passed; full desktop/mobile UI suite 78 passed. EventStream routes were asserted in both viewports.
- Alembic offline generation remains on single head `e1f2a3b4c5d6`; `git diff --check` passed. No production migration, data cleanup, or backfill was run.

Remaining work: fully migrate the solution catalog and technology list to Event/Entity, migrate Search, add Repository Detail, benchmark hotspot recall, complete historical backfill, and implement non-GitHub scoring.

### Remediation Review — 2026-10-24 (continued)

- Global search now indexes active V2 Events and their RawItem evidence, routes results to Event Detail, adds a community facet, and suppresses legacy rows when matching V2 evidence exists. Unmatched V1 rows and private workbench results remain available.
- Validation: backend 202 passed (one dependency deprecation warning); frontend production build passed; lint 0 errors / 10 warnings; frontend unit tests 7 passed; full desktop/mobile UI suite 80 passed. Search facet and Event navigation were checked on both viewports.
- Alembic offline SQL generation still yields the single head `e1f2a3b4c5d6`; `git diff --check` passed. No production database migration, data cleanup, or historical backfill was performed.

Remaining work: migrate the full solution catalog and technical project list, add Repository Detail, execute benchmark-backed hotspot recall, complete historical backfill, and implement non-GitHub scoring. Search SQL is unit-verified with a mocked DB connection; it has not been executed against an isolated PostgreSQL instance.

This remediation checkpoint does not change the full-acceptance status: V2 remains not fully accepted until the open P0 items are implemented and validated.

### Remediation Review — 2026-10-24 (continued)

- Repository Detail now reads the shared Entity endpoint for repository identity, active Events, Evidence, metric history, and growth windows. Technology EventStream links repository Entities to this detail view; other Entities continue to link to Event Detail.
- Search SQL now aggregates source names from Evidence while preserving active V2 Event results and compatibility suppression for matching legacy rows.
- Full validation: backend `pytest -q` 204 passed (1 dependency deprecation warning); frontend unit tests 7 passed; Playwright desktop/mobile suite 82 passed; source lint 0 errors / 10 warnings. The initial broad lint command was killed (137) after traversing generated Playwright trace assets; linting `src/` completed successfully.
- Alembic offline SQL generation succeeded through the single head `e1f2a3b4c5d6`; `git diff --check` passed. No production database connection, migration, backfill, cleanup, or historical data modification was performed.
- Browser tests continue to report React hydration attribute warnings in existing routes (including input caret styling); tests pass, but the underlying warnings remain to be triaged.

Remaining work: migrate the full solution catalog and complete technology project list onto the shared Entity/Event model; benchmark hotspot recall and add broader discovery adapters; complete historical backfill (only after an isolated data validation plan); add non-GitHub scoring; and verify the new Search SQL and Repository Detail queries against an isolated PostgreSQL database. Full V2 acceptance remains open.

### Remediation Review — 2026-10-23

- Discovery candidates now inherit the configured `business_scopes` from Source Registry, including multi-scope aggregation across corroborating sources. The fixed source-key mapping remains only as compatibility fallback for rows without scope metadata.
- Added regression cases for arXiv technology routing and an admin-edited Hacker News scope. Focused Discovery tests: 7 passed; full backend suite: 206 passed (1 dependency deprecation warning); `git diff --check` passed.
- No schema change or data write/backfill was introduced. Production database and historical data remain untouched.

Next review: source adapters still use a fixed set of collectors, so creating arbitrary sources is not yet supported; broader hotspot recall needs a measured benchmark and additional discovery coverage. Solution catalog and technology list retain V1-backed detail flows alongside V2 Event streams.

### Remediation Review — 2026-10-23 (Source Registry / Discovery)

- Source Registry now supports creating disabled sources for the four adapters implemented by Discovery Sentinel (`product_hunt_feed`, `hacker_news_api`, `hugging_face_api`, `arxiv_api`); the collector enumerates enabled registry entries and uses each entry's configured URL. Admins can edit source name and URL, test before enabling, and set business scopes, authority, priority, and schedule. Shared Sentinel schedules stay synchronized and are applied to the running APScheduler job.
- Candidate routing reads configured business scopes and aggregates scopes from corroborating sources. Verified product candidates are identified by evidence kind rather than a fixed source key, so additional Product Hunt adapter entries remain usable.
- Validation: backend `pytest -q` 211 passed (1 dependency deprecation warning); focused Source/Discovery/API tests 51 passed; frontend `npm run build` passed; source lint 0 errors / 10 warnings; frontend unit tests 7 passed; desktop/mobile UI tests 82 passed; `git diff --check` passed.
- No migration or database changes were needed; no production database, historical data, or existing Source rows were modified. New sources are deliberately created disabled and enter collection only after an admin enables them.

Remaining gaps: adapters outside the four Sentinel formats still require code integration; Source Connection test and collection have not been exercised against a live external source in this validation. Full-catalog Entity migration, benchmark-based recall measurement, non-GitHub scoring, and isolated PostgreSQL query validation remain open.

### Remediation Review — 2026-10-23 (Scoring)

- Added deterministic `signal_hot_v1` scoring for non-GitHub Events. It scores positive 24-hour MetricSnapshot changes, evidence/source corroboration, highest source authority, and recency; it does not use absolute popularity or AI-generated facts. The response stores a formula version, component values, and metric basis.
- Candidate approval persists the generic score. Admin Re-score now supports all active Events; GitHub Events continue using the existing `github_hot_v1` formula.
- Newly observed RawItems for already approved candidates now attach to the existing active Event, advance its seen-time range, and trigger a fresh score. Archived/ignored Events are not restored automatically.
- Validation: backend `pytest -q` 216 passed (1 dependency deprecation warning); Discovery/scoring/Event focused tests 14 passed; frontend production build passed; source lint 0 errors / 10 warnings; frontend unit tests 7 passed; desktop/mobile UI suite 82 passed; `git diff --check` passed.
- No schema change, migration, backfill, production database access, or data cleanup was performed.

Remaining work: calibrate scoring against a labeled historical benchmark before claiming measured hotspot recall; extend collection beyond the four Discovery adapters; migrate remaining catalog/list reads; and run database-backed validation in an isolated PostgreSQL environment. The formula is deterministic and explainable, but its weights are not yet benchmark-calibrated.

### Remediation Review — 2026-10-23 (GitHub Discovery / Full Regression)

- Discovery Sentinel now includes a registry-managed GitHub Search source. Six bounded, single-term searches cover recent Agent, MCP, LLM, inference, generative-AI, and AI repositories; results are deduplicated, stored as RawItems against canonical `github:owner/repo` Entities, and persist Stars/Forks MetricSnapshots. Search calls are serialized and spaced to stay within GitHub's unauthenticated search quota.
- Candidate evaluation uses relative metric movement across snapshots, so a small repository's rapid growth can qualify while a one-time high Star total does not. Approving a repository candidate reuses the canonical existing GitHub Trending Event when available and adds evidence instead of creating a parallel event.
- Added the additive GitHub Search Source migration (`f2a3b4c5d6e7`) and exposed its supported adapter in Source Registry API and admin UI. The migration chain has one head, `f3a4b5c6d7e8`; offline SQL generation passed. No migration was applied to a database; no data was deleted or changed.
- Full validation: backend 231 passed; frontend production build passed; frontend unit tests 7 passed; Playwright desktop/mobile UI suite 82 passed; source lint 0 errors / 10 warnings; `git diff --check` passed. A focused Discovery rerun passed 13 tests after adding the rate-limit regression case.
- Acceptance remains partial at this checkpoint: UI output continues to show existing React hydration attribute warnings; score weights lack labeled benchmark calibration; schema/API checks had not yet been run against an isolated PostgreSQL instance; no historical backfill or end-to-end production collector run was performed. The GitHub source is enabled by migration and will begin scheduled collection after that migration is deployed.

### Remediation Review — 2026-10-23 (PostgreSQL Chain / Data Path)

- Started a disposable local PostgreSQL 16 container isolated from the running application databases. With a minimal V1 baseline schema, applied the full Alembic chain from the initial stamp through `f3a4b5c6d7e8`; all revisions completed and the resulting DB reported the expected head.
- Exercised the real service code against that PostgreSQL DB: create/enable/edit Sources and schedules → persist GitHub and community RawItems → create shared repository Entity and Stars/Forks Metrics → discover a two-source Candidate → approve it into an Event → read Event Evidence, Entity Metrics, and score. The path passed with one Candidate, one Event, two Evidence rows, four Metric rows, and a stored `signal_hot_v1` score.
- The PostgreSQL run caught a psycopg placeholder error in the GitHub Trending Event match (`LIKE` wildcard embedded in query text). Changed it to a parameterized pattern and added a regression assertion; the end-to-end DB path passed after the fix.
- This validates migration execution against a minimal compatibility baseline and core service SQL. It does not establish that every V1 production schema variant or production dataset migrates cleanly; full historical migration and production collection remain unrun, and no production database or historical record was touched.
- Added opt-in repeatable PostgreSQL integration coverage (`INSIGHT_POSTGRES_TEST_URL`) for the persisted Source → RawItem → Entity/Metric → Candidate → Event path and benchmark-coverage SQL, with cleanup scoped to its generated test keys. The isolated run passed (1 test); standard backend suite passed 235 tests with this opt-in case skipped when no test DB is configured.
- Extended the isolated DB check through Event merge/split and Source failure health recording; all three operations passed. The full backend run also caught and fixed a startup catch-up `run_task` import scoping error; stale-analysis test fixtures now carry the freshness fields introduced by the latest migration.

### Remediation Review — 2026-10-23 (Hotspot Coverage Audit)

- The admin Coverage API now reports the 24-hour share of enabled benchmark-source RawItems linked to a Candidate or active Event, broken down by source, and lists unlinked items with a review reason. The UI states this exact denominator; it does not present it as recall across the entire Internet. GitHub Search is also recognized as a supported adapter in coverage status.
- Added an API regression for a mixed 50% represented/unlinked sample. Added opt-in PostgreSQL integration test refuses non-loopback or non-test-named databases; it passed against a disposable PostgreSQL database and cleans up only its generated keys.
- Latest regression: backend 236 passed / 1 opt-in DB test skipped by default; explicit PostgreSQL test 1 passed; frontend build and 7 unit tests passed; desktop/mobile UI suite 82 passed; source lint 0 errors / 10 existing warnings; `git diff --check` passed.
- Remaining coverage limitation: this is an observed benchmark-source flow-through rate, not a recall benchmark against an independently maintained labeled set. Unlinked reason is an actionable review hint; individual discovery-threshold attribution is still not stored.

### Remediation Review — 2026-10-23 (Cache / Email Operations)

- Community snapshot cache now keys on enabled community Sources and their configured URLs; the collector requests those registry URLs instead of hard-coded endpoints. Source disable/enable and URL edits therefore invalidate the 15-minute cache. A migration corrects only the two unchanged legacy defaults (Baidu board URL and CSDN pagination URL); a real PostgreSQL upgrade confirmed an administrator-customized CSDN URL is preserved.
- Both administrator manual email paths now record per-brief delivery attempts in `email_delivery_attempts` and update `last_sent_at` only after both briefs succeed. Scheduled retries still skip the brief already delivered that day and record failures for retry.
- Validation: backend 237 passed / 1 opt-in PostgreSQL test skipped; community cache/source tests 5 passed; email scheduling/retry tests 5 passed; migration offline generation and isolated PostgreSQL upgrade to `f4a5b6c7d8e9` passed; `git diff --check` passed. No production migration, email send, or historical data change was performed.
- Remaining operations gap: no external alert transport is configured for repeated Source/Collector/AI/Email failures; errors remain visible through admin health/task/email-delivery views and logs. UI build was not rerun because no frontend files changed this round.

### Remediation Review — 2026-10-23 (Discovery / Task Failure Visibility)

- Discovery Sentinel now includes per-source fetch failures in its result while retaining the number of candidates discovered. The shared task runner records `partial`, `partial_success`, and `failed` results as failed task runs and copies source error details into the task error field, so the existing Admin task and coverage views no longer report these runs as successful.
- Added regression tests for both Discovery partial results and persisted task failure details. Validation: full backend suite 239 passed / 1 opt-in PostgreSQL test skipped; `git diff --check` passed. No schema change, database migration, frontend change, production task, or data cleanup was performed.
- Remaining gap: task status uses the existing binary success/failed display, so a partially completed task is shown as failed while its result payload retains the partial status and successful counts. No external alert transport is configured.

### Remediation Review — 2026-10-23 (Solution Catalog Event Linking)

- Daily catalog refresh now writes every active legacy solution and solutions removed that day into the V2 RawItem → Entity → Event → Evidence chain. Baseline entries use a stable catalog-entry Event; later changes retain separate change Events. Existing catalog records and fields remain intact.
- The catalog API associates each solution with its latest active V2 Event, and the UI exposes an Event Detail link when that association exists. Existing directory filters, official source links, summaries, and workbench actions remain available.
- Validation: backend `pytest -q` 240 passed / 1 opt-in PostgreSQL test skipped; frontend production build passed; ESLint 0 errors / 10 existing warnings; Alembic offline SQL generation passed at the single head `f4a5b6c7d8e9`; `git diff --check` passed. The V2 baseline write was run twice against a disposable PostgreSQL 16 instance and confirmed idempotency (1 Event, 1 Evidence); the catalog API returned its Event ID. No schema change, migration, production collection, data deletion, or cleanup was performed.
- Backfill is incremental and happens during a successful daily catalog refresh; existing rows will not have Event links until that refresh succeeds. The live isolated check exercised the baseline write and catalog-link query, but not the entire crawler refresh against vendor sites. The catalog directory still reads compatibility fields from the V1 table while Event Detail and EventStream use V2.

### Remediation Review — 2026-10-23 (Technology Repository Read Path)

- The Technology Ecosystem current-project list now reads `/api/v2/repositories/trending`, selecting the latest GitHub Trending RawItem per canonical repository Entity and linking it through active Event Evidence. It returns `entity_key` and `event_id`; project cards link to Repository Detail and Event Detail. The title now reflects the broader Technology Ecosystem page, with cross-source EventStream above the GitHub project snapshot.
- The V2 endpoint is read-only. If no V2 snapshot exists for a requested period, it reads the V1 trending archive without triggering a crawl; existing `/api/github-trending` and historical/evaluation routes remain compatible. Snapshot date filtering uses Asia/Shanghai to match the crawler's collection date. Fixed the hotspot evaluation callback's stale locale dependency.
- Validation: backend `pytest -q` 247 passed / 1 opt-in PostgreSQL test skipped; isolated PostgreSQL 16 query returned the expected Entity/Event IDs and snapshot values; targeted desktop/mobile Playwright tests 2 passed; frontend production build passed; frontend unit tests 7 passed; lint 0 errors / 9 warnings; `git diff --check` passed. No schema change, migration, production database access, or data cleanup occurred.
- Remaining: V1 fallback remains necessary until scheduled collection has populated V2 snapshots for legacy-only dates. Historical project browsing and business evaluations still use V1 compatibility tables; broader non-GitHub Technology Ecosystem signals are available in EventStream, but the GitHub-specific ranked snapshot remains GitHub-only by design.

### Remediation Review — 2026-10-23 (Repository Business Evaluation / Full Regression)

- Repository business evaluation now reads shared V2 repository Events/Entity metrics, stores the canonical analysis by Entity key, and attaches the business score to the active Event. The existing V1 evaluation table remains a compatibility projection; evaluation reads prefer V2 and no longer trigger a live crawl. Old V1 history remains readable.
- The evaluation prompt is seeded in Prompt Registry (`repository_business_eval`, published version 1); analysis responses carry the prompt name/version. The startup catch-up and scheduled/manual evaluation paths use the V2-aware evaluator. Technical email selects V2 repository Events/evaluation first, and Repository Detail exposes the concise business assessment.
- For staged deployment, the V2 Trending UI read falls back to the existing V1 read only on HTTP 404, when the deployed backend does not yet expose the new route. Partial task results now retain a visible error reason in task health.
- Validation: backend `pytest -q` 253 passed / 2 opt-in PostgreSQL tests skipped without `INSIGHT_POSTGRES_TEST_URL`; disposable PostgreSQL 16 evaluation path passed, including the seeded Prompt Registry record, canonical `intelligence_analysis`, Event score, and V2 read; Alembic offline SQL generation passed at the single head `b0c1d2e3f4a5`; frontend production build passed; frontend unit tests 7 passed; ESLint 0 errors / 9 warnings; full Playwright desktop/mobile suite 84 passed; `git diff --check` passed. No production DB, email delivery, historical-data cleanup, or production backfill was run.
- Remaining: Repository historical browsing still falls back to V1 history; technical email does not yet include the full requested activity/contributor/release/maturity/deployability evidence; AI provider execution and admin prompt edit/rollback were not exercised. The currently running application backend returned 404 for the V2 Trending route, so compatibility fallback is needed until deployment. Browser runs continue to log existing hydration attribute mismatches (including caret styling), although all UI tests passed. Overall V2 acceptance remains open.

### Remediation Review — 2026-10-23 (Technical Email Evidence)

- Repository Event reads now join the latest matching GitHub Search RawItem, exposing its observed `pushed_at` and repository Topics to the technical email. The email uses the stored Event hot-score Stars delta when present, retains the reported daily increase as a compatibility fallback, and labels the observed last push and topics. It explicitly reports contributor counts and release records as not yet collected rather than inferring them.
- Validation: email/repository focused tests 8 passed; full backend suite 253 passed / 2 opt-in PostgreSQL tests skipped; `git diff --check` passed. No schema change, migration, frontend change, production database operation, email send, or data cleanup was performed.
- Remaining: contributor counts and release evidence need collection and persistence; repository activity currently means GitHub's `pushed_at` observed by Discovery, not a full commit/contributor activity series. Engineering maturity, innovation, and deployability remain AI business-evaluation judgments with limited repository evidence and should not be presented as independently verified metrics. This increment narrows the email evidence gap but does not complete the technical email acceptance criteria.

### Remediation Review — 2026-10-23 (Repository Metadata / Release Evidence)

- The existing GitHub Trending collector now enriches at most the daily top 8 repositories using public GitHub REST data: last push, topics, license, contributor count, and the latest two releases. Per-repository metadata is cached for 24 hours and persisted as a RawItem on the existing `github_trending` Source; contributor count is recorded as a MetricSnapshot. The raw metadata is attached as evidence to the canonical repository Event.
- A release Event is created on that repository Entity. It is marked `repository_major_release` only when the latest and previous release tags are parseable semantic versions and the major number increased; otherwise it remains `repository_release`. Repository reads and technical email expose the observed release, contributor, license, activity, and topic facts; AI project analysis receives those same facts as evidence.
- Collection failures are returned in the GitHub task result and mark the source degraded/partial while preserving successfully collected Trending rows. No network request is made during page or email rendering. Existing Source Registry toggle and schedule continue to control the collector.
- Technical email also shows the existing D4 engineering/delivery score as an AI judgment. It remains distinct from the observed GitHub facts and is not presented as an objective metric.
- Validation: focused metadata/email/evaluation/PostgreSQL-test suite 29 passed / 3 opt-in PostgreSQL tests skipped; full backend suite 259 passed / 3 skipped; a disposable PostgreSQL 16 schema check exercised metadata upsert twice, contributor MetricSnapshots, Release Event deduplication, and V2 Repository read; `git diff --check` passed; Alembic remains at `b0c1d2e3f4a5`. No migration, production DB operation, or historical data change occurred.
- Remaining: enrichment is limited to 8 daily Trending projects and unauthenticated GitHub REST quota/real scheduled collection have not been validated; non-semver release series cannot be classified as major. Activity is the latest observed push date, not a commit frequency series. Innovation is not yet a structured analysis dimension, while engineering maturity and deployability share the existing D4 judgment and still need stronger, inspectable evidence. Full V2 acceptance remains open.

### Remediation Review — 2026-10-23 (Generic RSS/Atom Discovery)

- Source Registry now accepts an `rss_feed` adapter. Enabled sources run through the existing Discovery Sentinel schedule and persist RSS 2.0 / Atom entries as RawItems before Candidate aggregation; no separate page or duplicate event pipeline was introduced. Feed redirects are rejected, while Source creation retains HTTPS validation and the existing disabled-by-default workflow.
- Coverage now includes RSS observations, so unrepresented feed items appear in the existing benchmark coverage view. The admin Source form exposes the adapter.
- Completed: generic feed source can enter the existing registry → RawItem → Candidate → Event path, with Coverage visibility.
- Changed files: `backend/services/discovery_service.py`, `backend/services/source_registry_service.py`, `backend/services/task_service.py`, `backend/routers/intelligence_v2.py`, `backend/tests/test_discovery_service.py`, `backend/tests/test_source_registry_service.py`, `frontend/src/app/admin/sources/page.tsx`, `DATA_AUDIT.md`.
- Database: no schema change or migration; production database was read-only inspected (head `c1d2e3f4a5b6`, 10 Source rows). No data was changed or deleted.
- API: `/api/v2/admin/sources` accepts `adapter: rss_feed`; existing create/list/enable/run interfaces are reused.
- Validation: full backend suite 277 passed / 3 skipped; Source page ESLint passed; Next production build passed; Alembic reports one head `c1d2e3f4a5b6`; `git diff --check` passed.
- Risks: external RSS endpoint behavior and a full live collection have not been exercised; RSS entries without a stable guid use the canonical link as identity. Production deployment was not attempted because the current Compose image versions are being changed concurrently and the prior deploy encountered a container-name conflict. Existing Docker health probes had passed; the old competing systemd target remains disabled to avoid port contention.
- Next: verify the deployment/version state is stable, then validate the Source create → manual collection → Coverage path against an isolated database and a controlled feed; continue consolidating homepage/business/email reads on shared Events and measuring hotspot recall.

### Remediation Review — 2026-10-23 (Business Email Event Brief)

- When active V2 Events exist, the commercial email now uses a compact Event-based brief: up to three high-scoring recent Events, recent business-scope counts, observed source/evidence counts, and cached impact only when the analysis references that same `event_id`. It links directly to Event Detail. If there are no V2 Events, the previous V1-compatible board email remains available.
- Changed files: `backend/services/email_dashboard.py`, `backend/tests/test_email_scheduling.py`, this record.
- Database/API: no schema or endpoint changes; read-only reuse of `event_service.list_events` and existing board analysis cache.
- Validation: focused email suite 7 passed; full backend regression 279 passed / 3 isolated PostgreSQL tests skipped; `git diff --check` passed; system end-to-end health check passed. No email was sent and no data changed.
- Risk: the brief ranks among the latest 100 active Events because the shared list API is paginated; business-scope counts use that same window. Event score and evidence counts are shown only when present. No deployment was attempted while Compose backend image version continued changing concurrently (RC31 at last check vs production RC26).
- Next: complete full backend regression and then proceed to the remaining shared-read-path and deployment audit; production rollout remains pending a stable Compose version.

### Remediation Review — 2026-10-23 (Isolated PostgreSQL Acceptance)

- Created a disposable loopback PostgreSQL 16 database, constructed the minimal V1 compatibility baseline, stamped at `a7b8c9d0e1f2`, and applied the remaining Alembic chain through `c1d2e3f4a5b6`.
- Extended opt-in DB integration coverage for RSS Sources: create/enable two registry entries → fetch controlled RSS responses → persist RawItems → aggregate one Candidate → approve one Event with two Evidence rows → confirm both Sources are represented in Coverage.
- Validation: all four PostgreSQL integration tests passed; the entire backend suite passed with the isolated DB configured (285 passed). This validates the current post-`a7` migration chain and core data path against the test baseline. It does not validate every historical V1 schema variant or execute a backfill against production.
- The first integration run exposed missing legacy baseline tables (`vendor_ai_applications`, `platform_task_runs`, `runtime_settings`); the isolated baseline was corrected and the final full run passed. No application schema/migration code was changed as a result; production data was not used.

#### Runtime follow-up

- During final verification, an external deployment replaced the backend with `insight-web-backend:1.0.0-rc.31`. Its baked Docker health command initially had invalid quoting and the backend briefly stopped responding. The deployment recovery process restarted it; the current backend and frontend are healthy and `scripts/health-check.sh full` passes. The RC31 container is healthy, while frontend remains the existing image SHA `60b227f2ff40`.
- After health recovery and confirming no build/deploy process remained, removed dangling images only; Docker reclaimed 1.76 GB and now reports none. Stopped named rollback containers were preserved.
- Deployment/code parity remains unverified: `scripts/check-version.py` still fails because Compose references backend RC31 while package/version metadata remains RC26, and the running image's source revision is not the current `HEAD`. The RSS and Event-based email changes in this working tree therefore cannot be claimed as deployed.

### Remediation Review — 2026-10-23 (Shared Event Homepage / Runtime Recheck)

- Replaced the old homepage Radar rendering with the shared `/api/v2/events` feed; the lead, counts, business coverage and event list now derive from the same Event IDs and Event Detail links. Removed the obsolete Radar marker helper and its unused homepage styles/tests.
- Fixed a psycopg2 SQL formatting defect in global search: the literal `LIKE 'v2:%'` pattern is escaped as `LIKE 'v2:%%'` before parameter binding. Added a regression assertion; focused search tests pass. This fix is in the worktree only.
- Validation: backend default suite 284 passed / 4 isolated-PostgreSQL tests skipped; isolated PostgreSQL full suite previously passed 285 tests including the RSS Source → RawItem → Candidate → Event → Coverage path. Frontend lint passed with 9 pre-existing warnings, 6 unit tests passed, and production build passed. Full Playwright run: 87 passed / 1 intermittent homepage navigation failure; that test passed when rerun alone. `git diff --check` passed.
- Runtime recheck: backend RC34 is healthy, but production `/api/search?q=agent` still returns 500 with the confirmed unescaped-percent stack trace because the running image predates the worktree fix. Frontend serves `/` with HTTP 200 but is unhealthy because its probe proxies to `backend:8000`, while the current running backend container lacks the `backend` DNS alias. `scripts/check-version.py` still fails (Compose backend RC34 vs package/metadata RC26). No container was restarted, no production data was written, and dangling-image cleanup was not repeated.
- Risks/next: align package/lock/version/docs with the intended release and make deployment create the expected network alias, then deploy once and recheck frontend health and live search. Existing hydration mismatch diagnostics (browser-injected `caret-color`) and 9 lint warnings remain. Do not treat current RC34 as containing the uncommitted search fix.

### Remediation Review — 2026-10-23 (RC36 Search Canary / RC37 Frontend Rollout)

- RC36 canary exposed the production `competitor_news` schema mismatch in global search; the canary/live RC36 image now uses `link AS url`, and read-only searches plus `/api/v2/events` returned HTTP 200. The production main backend remains RC36 and healthy.
- Fixed frontend proxy configuration to use the stable `insight-backend` container DNS name. Built and deployed frontend RC37 without restarting the backend; the old RC26 frontend is retained, stopped, as `insight-frontend-rc26-rollback`.
- Upgraded Next.js to 16.4.2, aligned `eslint-config-next`, moved Typography to development dependencies, and updated compatible transitive dependencies. The patched Next.js line is above the affected range in the upstream security advisories. Production dependency audit is clean; 8 development dependency findings remain (6 high, 2 moderate), including the ESLint and typography plugin trees.
- Validation: version consistency and Compose syntax pass; frontend lint, 6 unit tests, production build and all 88 desktop/mobile Playwright tests pass. Production frontend home, health probe and proxied global search return HTTP 200; RC36 canary Event API returns HTTP 200. Backend focused search tests pass (2); isolated PostgreSQL end-to-end V2 chain and full backend suite were verified in the prior entry.
- Runtime: frontend RC37 healthy; backend RC36 healthy. One `vendor_ai_applications` analysis remains pending; other pending source-backed analyses advanced from 191 to 219 completed during the observed batch. Backend RC37 promotion is deferred until this analysis exits to avoid interruption. Compose and package metadata are already RC37.
- Operational risk: environment values were inadvertently expanded in a Compose inspection tool output during this session. No secret values were copied into repository changes or the user-facing response. Rotate affected database, model-provider, and SMTP credentials, then update deployment secrets and verify dependent services.

### Remediation Review — 2026-10-23 (RC37 Backend / Scheduler Recovery)

- Added startup repair for orphaned `platform_task_runs`: each `running` task is marked failed only after its task-key PostgreSQL advisory lock can be acquired; active tasks are skipped, and existing run rows are retained. No schema change or migration is required.
- Backend RC37 was built from the worktree and deployed after confirming there were no active task rows or AI application analyses. Full backend tests: 286 passed / 5 opt-in PostgreSQL tests skipped; the isolated PostgreSQL data path remains covered by the prior recorded run. The recovery logic has a unit test plus a disposable PostgreSQL 16 integration test covering free and held advisory locks; the isolated test passed.
- Final runtime check: backend and frontend are both RC37 and healthy; `/api/v2/events`, global search through both backend and frontend proxy, and `scripts/health-check.sh full` pass. Production Alembic reports `c1d2e3f4a5b6 (head)`. The application analysis table has 220 completed rows and no pending rows; there are no task runs currently marked running.
- Cleanup: removed dangling images after successful health checks; reclaimed 2.816 GB. Named RC36/RC26 rollback containers were retained, and no database rows were deleted.
- Final recheck: frontend unit tests 6/6 and full Playwright desktop/mobile suite 88/88 passed after the dependency changes; `npm audit --omit=dev` reports 0 findings.
- Remaining: four PostgreSQL tests are skipped when the opt-in test URL is absent; full historical V1 migration variants, actual email delivery, credential rotation, and broader remaining V2 acceptance items have not been completed in this entry. Production/development dependency audits differ: production is clean, while the development tree still has 7 findings (5 high, 2 moderate).

### Remediation Review — 2026-10-23 (RC37 Acceptance Recheck)

- Rechecked deployed RC37: backend/frontend containers are healthy, `scripts/health-check.sh full` passes, and `/api/v2/repositories/trending?limit=1` returns HTTP 200 with V2 Event-backed rows. The earlier V2 Trending 404 deployment limitation is resolved.
- Validation: backend `pytest -q` 286 passed / 5 opt-in PostgreSQL tests skipped; frontend unit tests 6/6; full desktop/mobile Playwright suite 88/88; Next production build passed; ESLint 0 errors / 11 warnings; `scripts/check-version.py` and `git diff --check` passed. No database writes, migration, email delivery, or data cleanup performed.
- Remaining: opt-in database tests were not rerun because the expected disposable PostgreSQL container was absent; full historical V1 schema variants, live email delivery, external failure alerting, actual credential rotation, and remaining V2 acceptance gaps remain open. Playwright continues to report hydration attribute mismatches caused by injected caret styling.
- Image cleanup check: one 447 MB dangling image remains because the running `server-inventory` container uses it. `docker image prune -f` reclaimed nothing; removing or stopping that unrelated service was outside this V2 rollout.

### Remediation Review — 2026-10-23 (Repository Assessment Evidence Gate)

- Technical repository scores now require dimension-specific observed evidence: engineering maturity accepts activity, contributor and release evidence; innovation accepts project description, topics or release notes; deployability accepts description, license or release evidence. Popularity-only fields such as Stars and Forks can no longer justify these scores. Invalid or absent evidence produces a null score and the existing “evidence insufficient” explanation.
- Changed files: `backend/services/hotspot_service.py`, `backend/tests/test_business_evaluation.py`, this record.
- Validation: focused evaluation/email tests 24 passed; full backend suite 286 passed / 5 opt-in PostgreSQL tests skipped; `git diff --check` passed. No database, migration, API, email, or production deployment changes.
- Risk: this is a provenance gate on model-provided evidence keys, not independent verification of the model's written reasoning; the email correctly presents these as AI judgments. Evidence quality still depends on the stored GitHub observations.
- Deployment: published as RC38 via the repository Docker deployment script. Backend and frontend are healthy; backend health, V2 Events, V2 Repository, frontend search proxy and full end-to-end health checks returned 200/pass. Version consistency and `git diff --check` pass. Docker prune reclaimed 1.401 GB; the 447 MB dangling image referenced by the running `server-inventory` container remains in place.
- Acceptance remains partial: five opt-in PostgreSQL tests, historical V1 schema variants, real email delivery, external alert transport, credential rotation and labeled hotspot-recall benchmark remain unverified or outstanding. Full browser suite was run before this backend-only behavior change and passed 88/88; the release script rebuilt the frontend successfully.

### Remediation Review — 2026-10-23 (Full PostgreSQL Integration Recheck)

- Replayed the Alembic chain in a disposable PostgreSQL 16 container from the initial `beb54db85b7f` stamp to `c1d2e3f4a5b6`, using a minimal V1 compatibility baseline. All migrations applied successfully, including the source registry, Event/Evidence, candidate, prompt and email-delivery schemas.
- Ran the entire backend suite with the loopback-only opt-in test URL against that database: 291 passed, 0 skipped. This includes all five PostgreSQL integration cases for Source/RawItem/Candidate/Event/Coverage, RSS aggregation, repository analysis persistence, and orphaned task recovery. The first run identified missing tables/columns in the handcrafted test baseline; after correcting only that disposable baseline to match the existing V1 contracts, the full suite passed.
- The ephemeral database container was removed after the run. No production database, production data, migration code, or historical records were changed.
- Remaining: this validates one explicit minimal V1 baseline, not every historical V1 schema variant or production backfill; real email delivery, external alert transport, credential rotation, and labeled hotspot-recall benchmarking remain open.

### Remediation Review — 2026-10-23 (Local SMTP Wire Acceptance)

- Exercised the existing `send_email` implementation against a temporary loopback TLS SMTP sink using test-only credentials and `.invalid` sender/recipient addresses. Two messages completed TLS, SMTP AUTH LOGIN, MAIL/RCPT/DATA delivery, and were captured with the expected subjects, recipients, and both `text/plain` and `text/html` MIME parts.
- The test sink and its self-signed certificate were temporary and removed by the test process. No external SMTP relay, production subscriber, email delivery-attempt row, or production data was used.
- This closes SMTP client/protocol and MIME handoff validation only. External relay authentication, mailbox acceptance/delivery, bounce handling, and deliverability remain unverified pending a controlled SMTP provider test.
