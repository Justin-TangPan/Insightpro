# InsightPro 数据库契约

**基线日期**：2026-08-25

**状态**：已与当前 PostgreSQL、后端 SQL 和 Prisma schema 对齐

**事实来源**：`frontend/prisma/schema.prisma`、`backend/services/startup_service.py`、后端读写 SQL

## 1. 约定

- Supabase PostgreSQL 是唯一生产业务存储。
- `frontend/prisma/schema.prisma` 用于记录 public 表契约；后端当前通过 `psycopg2` 直接访问数据库。
- Supabase Auth 用户位于认证系统，不在 public schema 建模。
- 业务日期目前以 `TEXT` 保存 `YYYY-MM-DD`，时间计划以 `HH:MM` 保存。
- 启动时 `ensure_runtime_schema()` 幂等补齐当前必要字段、表和索引。

## 2. 表清单

| 表 | 用途 | 主去重规则 |
|---|---|---|
| `github_trending` | GitHub Trending 快照 | `scrape_date + category + repo_name` |
| `trending_business_eval` | 项目用途摘要与价值评估 | `scrape_date + repo_name` |
| `aliyun_solutions` | 阿里云方案目录及变化状态 | `url` |
| `cloud_vendor_news` | 云厂商官网动态 | `crawl_date + vendor + title` |
| `competitor_news` | 友商动态摘要 | `scrape_date + vendor + title` |
| `baidu_hotsearch` | 辅助热搜快照 | `scrape_date + title` |
| `scrape_log` | 采集运行记录 | 无复合唯一约束 |
| `insight_tasks` | AI 分析任务与报告 | 字符串 `id` |
| `email_subscribers` | 邮件订阅和排期 | `email` |
| `page_visits` | 页面访问埋点 | 自增 `id` |

## 3. 字段契约

### `github_trending`

| 字段 | 类型 | 空值 | 说明 |
|---|---|---|---|
| `id` | serial | 否 | 主键 |
| `scrape_date`、`scrape_time` | text | 否 | 采集日期与时间 |
| `repo_name` | text | 否 | `owner/repository` |
| `repo_url`、`description`、`language` | text | 是 | 项目信息 |
| `stars`、`forks`、`today_stars` | text | 是 | GitHub 展示值 |
| `tags` | text | 是 | 标签 |
| `category` | text | 否 | `daily` / `weekly` / `monthly` |
| `created_at` | timestamp | 否 | 创建时间 |

索引：`scrape_date`、`category`。

### `trending_business_eval`

| 字段 | 类型 | 空值 | 说明 |
|---|---|---|---|
| `id` | serial | 否 | 主键 |
| `scrape_date`、`repo_name` | text | 否 | 业务日期与项目名 |
| `repo_url`、`language`、`stars` | text | 是 | 项目快照 |
| `summary` | text | 是 | 项目用途速读 |
| `d1`、`d2`、`d3`、`d4`、`total` | double precision | 是 | 四维评分与总分 |
| `level`、`recommendation`、`reasoning` | text | 是 | 评级、建议与依据 |
| `eval_time` | text | 是 | 评估时间 |
| `created_at` | timestamp | 否 | 创建时间 |

索引：`scrape_date`。

### `aliyun_solutions`

| 字段 | 类型 | 空值 | 说明 |
|---|---|---|---|
| `id` | serial | 否 | 主键 |
| `title`、`url`、`category` | text | 否 | 方案标题、唯一链接和分类 |
| `source_description` | text | 是 | 官方描述 |
| `summary` | text | 否 | 20–30 字方案价值简介 |
| `content_hash` | text | 否 | 变化检测指纹 |
| `first_seen_date` | text | 否 | 首次发现日期 |
| `last_seen_date` | text | 否 | 最近仍存在日期 |
| `last_changed_date` | text | 否 | 最近内容变化日期 |
| `is_active` | boolean | 否 | 当前是否仍在官方目录 |
| `created_at`、`updated_at` | timestamp | 否 | 创建与更新时间 |

索引：`last_seen_date`、`last_changed_date`。

### `cloud_vendor_news`

字段：`id serial`、`crawl_date text`、`vendor text`、`title text`、`summary text?`、`url text?`、`category text?`、`created_at timestamp`。

索引：`crawl_date`。

### `competitor_news`

字段：`id serial`、`scrape_date text`、`vendor text`、`title text`、`link text?`、`summary text?`、`category text?`、`created_at timestamp`。

索引：`scrape_date`、`vendor`。

### `baidu_hotsearch`

字段：`id serial`、`scrape_date text`、`scrape_time text`、`rank integer?`、`title text`、`hot text?`、`link text?`、`created_at timestamp`。

索引：`scrape_date`。

### `scrape_log`

字段：`id serial`、`scrape_date text`、`scrape_time text`、`status text`、`items_count integer?`、`error_msg text?`、`created_at timestamp`。

### `insight_tasks`

| 字段 | 类型 | 空值 | 说明 |
|---|---|---|---|
| `id` | text | 否 | `task_*` 或系统基线 ID |
| `title` | text | 否 | 报告标题 |
| `status` | text | 否 | `pending` / `processing` / `completed` / `failed` |
| `data_sources` | json/jsonb | 是 | 输入来源 |
| `result` | json/jsonb | 是 | 结构化报告 |
| `error` | text | 是 | 截断后的失败原因 |
| `created_at`、`updated_at` | timestamp | 否 | 生命周期时间 |

索引：`status`、`created_at`。

### `email_subscribers`

| 字段 | 类型 | 空值 | 说明 |
|---|---|---|---|
| `id` | serial | 否 | 主键 |
| `email` | text | 否 | 唯一邮箱 |
| `name` | text | 是 | 接收人名称 |
| `active` | integer | 否 | `1` 启用，`0` 停用 |
| `weekdays` | integer[] | 否 | `0–6` = 周一至周日 |
| `send_time` | text | 否 | `HH:MM`，默认 `09:05` |
| `last_sent_at` | timestamptz | 是 | 防止同日重复投递 |
| `created_at` | timestamp | 否 | 创建时间 |

### `page_visits`

字段：`id serial`、`page_path text`、`visitor_id text`、`user_agent text?`、`referrer text?`、`created_at timestamp`。

索引：`page_path`、`visitor_id`、`created_at`。

## 4. 数据生命周期

```text
外部采集 / 用户操作
        │
        ▼
参数校验与质量过滤
        │
        ▼
INSERT ... ON CONFLICT / 内容指纹更新
        │
        ▼
public 业务表 ──► API 查询 ──► 页面、搜索、问答、报告、邮件
        │
        └──────► 新鲜度检查与定期清理
```

方案记录保留首次发现、最近出现和最近变化日期；采集快照通过复合唯一约束幂等写入；报告状态随任务执行更新。

## 5. 变更流程

1. 先修改后端建表/迁移逻辑与 SQL。
2. 同步 `frontend/prisma/schema.prisma`。
3. 更新本文档。
4. 执行 `cd frontend && npx prisma validate`。
5. 在非生产环境运行幂等 schema 校准并验证现有数据。

日期字段迁移、列删除和类型收紧都属于独立数据库迁移，不应仅依赖启动时校准。
