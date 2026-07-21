# InsightPro 数据库契约

**日期**：2026-07-09  
**状态**：后端契约版  
**来源**：`backend/reconcile_schema.py`、后端 SQL 调用、`frontend/prisma/schema.prisma`

> 说明：本次整改尝试连接 Supabase 进行在线 introspection，但当前执行环境 IP 不在 Supabase allow list 中，连接被拒绝。因此本文档以当前后端代码和 `reconcile_schema.py` 的幂等迁移逻辑作为数据契约来源。放通数据库 allow list 后，需要用实际库结构再次校验。

---

## 一、核心原则

1. `backend/reconcile_schema.py` 是当前数据库修复脚本。
2. `frontend/prisma/schema.prisma` 应与后端 SQL 使用的 public 表字段保持一致。
3. Supabase Auth 用户不在本 public schema 中建模，认证仍由 Supabase Auth 管理。
4. 后端日期字段当前大多使用 `TEXT` 保存 `YYYY-MM-DD`，后续如要迁移为 `DATE`，需要单独规划。

---

## 二、表结构摘要

### `github_trending`

GitHub Trending 抓取结果。

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | serial | 主键 |
| `scrape_date` | text | 抓取日期 |
| `scrape_time` | text | 抓取时间 |
| `repo_name` | text | 仓库名 |
| `repo_url` | text | 仓库链接 |
| `description` | text | 描述 |
| `language` | text | 语言 |
| `stars` | text | stars 文本 |
| `forks` | text | forks 文本 |
| `today_stars` | text | 今日新增 stars |
| `tags` | text | 标签 |
| `category` | text | daily/weekly/monthly |
| `created_at` | timestamp | 创建时间 |

约束：`unique(scrape_date, category, repo_name)`。

### `baidu_hotsearch`

百度热搜缓存。

字段：`id`、`scrape_date`、`scrape_time`、`rank`、`title`、`hot`、`link`、`created_at`。  
约束：`unique(scrape_date, title)`。

### `scrape_log`

爬虫运行日志。

字段：`id`、`scrape_date`、`scrape_time`、`status`、`items_count`、`error_msg`、`created_at`。

### `page_visits`

页面访问埋点。

字段：`id`、`page_path`、`visitor_id`、`user_agent`、`referrer`、`created_at`。  
索引：`page_path`、`visitor_id`、`created_at`。

### `email_subscribers`

邮件订阅者。

字段：`id`、`email`、`name`、`active`、`created_at`。  
约束：`unique(email)`。

### `competitor_news`

友商新闻摘要。

字段：`id`、`scrape_date`、`vendor`、`title`、`link`、`summary`、`category`、`created_at`。  
约束：`unique(scrape_date, vendor, title)`。

### `cloud_vendor_news`

云厂商官网动态。

字段：`id`、`crawl_date`、`vendor`、`title`、`summary`、`url`、`category`、`created_at`。  
约束：`unique(crawl_date, vendor, title)`。

### `industry_news`

行业新闻。

字段：`id`、`crawl_date`、`source`、`title`、`summary`、`url`、`category`、`created_at`。  
约束：`unique(crawl_date, source, title)`。

### `policy_updates`

政策更新。

字段：`id`、`crawl_date`、`source`、`title`、`summary`、`url`、`category`、`severity`、`created_at`。  
约束：`unique(crawl_date, source, title)`。

### `bidding_opportunities`

招标机会。

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | serial | 主键 |
| `bid_date` | text | 招标采集/发布日期 |
| `industry` | text | 行业 |
| `title` | text | 标题 |
| `procuring_entity` | text | 招标方 |
| `budget` | text | 预算原文 |
| `budget_amount` | integer | 预算金额，单位元 |
| `deadline` | text | 截止日期 |
| `summary` | text | 摘要 |
| `requirements` | text | 技术要求 |
| `qualification` | text | 资质要求 |
| `contact` | text | 联系方式 |
| `url` | text | 来源链接 |
| `source` | text | 来源 |
| `region` | text | 地区 |
| `status` | text | 状态 |
| `relevance_score` | real | 相关度 |
| `created_at` | timestamp | 创建时间 |

约束：`unique(bid_date, title)`。  
索引：`bid_date`、`industry`、`status`、`budget_amount`。

### `demand_signals`

需求信号。

字段：`id`、`signal_date`、`source_type`、`industry`、`title`、`summary`、`url`、`relevance_score`、`demand_tags`、`created_at`。  
索引：`signal_date`、`industry`、`source_type`。

### `demand_reports`

需求报告。

字段：`id`、`report_date`、`industry`、`title`、`content`、`created_at`。  
索引：`report_date`。

### `trending_business_eval`

GitHub Trending 业务价值评估。

字段：`id`、`scrape_date`、`repo_name`、`repo_url`、`language`、`stars`、`d1`、`d2`、`d3`、`d4`、`total`、`level`、`recommendation`、`reasoning`、`eval_time`、`created_at`。  
约束：`unique(scrape_date, repo_name)`。

### `insight_tasks`

AI 分析任务和报告结果。

字段：`id`、`title`、`status`、`data_sources`、`result`、`error`、`created_at`、`updated_at`。  
索引：`status`、`created_at`。

---

## 三、已消除的不一致

| 旧 Prisma 字段 | 当前后端字段 | 处理 |
|----------------|--------------|------|
| `BiddingOpportunity.date` | `bid_date` | Prisma 改为 `bidDate @map("bid_date")` |
| `BiddingOpportunity.link` | `url` | Prisma 改为 `url` |
| `DemandSignal.date` | `signal_date` | Prisma 改为 `signalDate @map("signal_date")` |
| `DemandSignal.source` | `url` | Prisma 改为 `url` |
| `CompetitorNews.date` | `scrape_date` | Prisma 改为 `scrapeDate @map("scrape_date")` |
| `EmailSubscriber.active` 缺失 | `active` | Prisma 已补 |
| `InsightTask` 旧关系模型 | `insight_tasks` 扁平任务表 | Prisma 改为后端实际使用模型 |

---

## 四、后续待办

1. 放通数据库 allow list 后执行真实 introspection。
2. 将高频 SQL 迁入 `backend/repositories/*`。
3. 为 schema 增加最小一致性测试，检查后端使用字段是否存在于 Prisma schema 文档。
4. 评估日期字段从 `TEXT` 迁移为 `DATE` 的成本。
