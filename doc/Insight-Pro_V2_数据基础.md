# Insight-Pro V2 数据基础

> 本文的设计与迁移步骤保留为历史背景。1.1.0 已将 V2 Event 接入首页雷达、社区/友商/解决方案/AI 应用等页面及管理审核流程；V1 表和兼容读取仍并存。来源采集与页面消费范围以当前代码和[版本记录](../log/versions.md)为准。

当前阶段接入 GitHub Trending、四个中文社区来源、阿里云/华为云方案目录和官方 AI 应用动态。旧表与旧 API 继续提供原有数据；来源采集完成后写入 V2 记录。

## 数据关系

`intelligence_sources` → `intelligence_raw_items` → `intelligence_event_evidence` → `intelligence_events`；`intelligence_entities` 关联事件与 `intelligence_metric_snapshots`。

- Source 保存来源、Adapter、业务范围、可信等级、排期和健康状态。
- RawItem 按来源与外部 ID 去重，保留采集时的原始字段和时间，不由 AI 修改。
- 社区热榜只写 RawItem；发布时间未核实，不直接生成正式 Event。
- 方案目录的首轮基线不生成 Event；后续新增、变更或下线记录同时保留旧表数据与 V2 Evidence。
- AI 应用的正式 feed/官方页面文本可进入 Evidence；产品目录和网络失败时的种子摘要不会生成 V2 Event。月份精度发布时间只保留在原表，V2 不补造具体日期。
- ai_app_official、aliyun_solutions、huawei_solutions 采集遵循 Source Registry 启停，并更新来源健康状态。
- Entity 的 GitHub 键为 `github:owner/repo`。
- Event 的 GitHub 键为 `github-trending:owner/repo`；多次观察共用同一事件 ID，证据逐次追加。
- MetricSnapshot 保存 Stars、Forks、各榜单的增长数字与排名；只有已有历史观测时才能计算变化。
- Event Detail 根据快照返回 1h、6h、24h、7d、30d 变化；窗口内没有可信基线时返回空值，并标明最新观测时间。
- GitHub HotScore 根据真实 Stars 增长计算，优先使用 24h 历史快照；历史不足时使用 GitHub Trending 原页提供的日增长数字。结果保存计算版本和依据。
- Audit 保存管理员启停来源的操作者与修改前后状态。
- 管理员合并 Event 时，来源事件转为 `merged` 并指向保留的 Event ID；证据仍可追溯，合并原因进入 Audit。

## API

- `GET /api/v2/events`：按最新观察时间列出正式事件，可用 `business_scope` 过滤。
- `GET /api/v2/events/{id}`：返回事件、原始证据和指标快照。
- `GET /api/v2/admin/sources`：管理员查看来源状态。
- `PATCH /api/v2/admin/sources/{source_key}/enabled`：管理员启停当前接入的 GitHub、社区、方案目录及 AI 应用来源并写入审计。Product Hunt 等未实现的 Adapter 返回 409。
- `POST /api/v2/admin/events/{source_id}/merge`：管理员提供 `target_id` 与 `reason` 合并事件；旧 ID 的详情查询解析到保留 ID。
- `POST /api/v2/admin/events/{id}/split`：将所选 Evidence 移到新 Event，保留 RawItem 并记录拆分原因。重复回填不会撤销人工拆分。
- `PATCH /api/v2/admin/events/{id}`：修改分类、业务范围、标签或状态；`POST /api/v2/admin/events/{id}/rescore` 重新计算支持的 GitHub HotScore。所有操作写入 Audit。

## 历史数据

升级 Schema 后，在后端目录运行 `python backfill_intelligence.py`。脚本按旧表 ID 分批回填 GitHub 历史快照；重复运行按稳定键去重。先在副本数据库验证行数和抽样证据，再在运行环境执行。

Radar、事件详情和多类业务页面已消费 V2 Event；邮件与首页还会组合快照、板块分析及兼容数据，尚非所有消费者都只读 V2。Source 管理支持已接入 Adapter 的配置和运行控制；创建全新 Adapter 仍需先实现对应 Collector。

## 本阶段状态

- V2 Schema 在临时 PostgreSQL 中从现有 V1 头 a7b8c9d0e1f2 增量迁移成功，未改动实际运行数据库。
- 目录事件和 AI 应用事件按稳定键去重；重复写入不会增加 RawItem、Event 或 Evidence。
- 空数据库从最早 Alembic revision 全量升级当前会失败，因为现有 V1 迁移链依赖部署前已存在的旧表。本次遵循项目既有方式从 V1 头验证；生产迁移前需确认目标库版本和表结构。
