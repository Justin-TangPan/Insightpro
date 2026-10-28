# Supabase 本地迁移验收与治理前快照

记录时间：2026-10-28（Asia/Shanghai）  
运行代码/部署标签：`1.1.5-rc.2`  
Alembic revision：`c5d6e7f8a9b0`  
数据原则：本次迁移未执行清洗、去重、合并、Backfill、Alembic upgrade/stamp 或业务 Schema DDL。

## 可回滚业务写入验收

测试表：`public.email_subscribers`（非事实/事件数据表）。

- 先经前端 `/api` 代理登录自建 Auth，后端验证临时管理员 Bearer token。
- 调用订阅写入 API 创建唯一测试记录，随后列表 API 能读到该记录。
- 调用管理员删除 API 完成软删除，再仅按随机测试邮箱物理清理测试记录；临时 Auth 用户也已删除。
- 另在后端数据库连接中执行 INSERT → UPDATE → SELECT，显式 `ROLLBACK`，新事务确认测试邮箱行数为 0。
- 写入、读取、API 权限检查和回滚均通过；健康检查通过。

权限边界：`email_subscribers` 当前没有启用 PostgreSQL RLS，也没有该表的 RLS policy；该 API 的权限由管理员 Bearer 验证和后端 `require_admin` 控制。此测试验证应用权限，不声称验证了该表的 RLS。当前全库 `pg_policies` 为 0。

## 治理前业务数据快照

| 对象 | 行数 / 值 |
|---|---:|
| `intelligence_raw_items` | 18,964 |
| `intelligence_candidates` | 465 |
| `intelligence_entities` | 5,314 |
| `intelligence_events` | 1,342 |
| `intelligence_event_evidence` | 13,218 |
| `github_trending` | 4,501 |
| `knowledge_chunks` | 1,304 |
| `email_subscribers` | 11（测试行已清理） |
| `auth.users` | 5 |
| Event → Raw Evidence 孤立引用 | 0 |
| Event Evidence 关系指纹 | `5b0ffa5d2d0998c733ee08e86faa8a76` |
| 最新 Raw `observed_at` | `2026-10-28 03:18:00+00:00` |

迁移前后业务表行数一致；Evidence 的 `(event_id, raw_item_id, evidence_role)` 指纹一致。Auth 用户的 ID、邮箱、用户/应用元数据与密码哈希组合指纹一致。完整云端导出、本地最终导出及原先本地数据目录均保存在受限权限的 `/var/backups/insight-supabase/`。

业务 Schema 摘要：public 有 103 个 constraint、127 个 index；迁移前后数量一致。Alembic revision 未变化。业务表 count 全部一致；仅 Realtime/Storage 内部 migration 账本的行数有版本差异。

## Supabase 系统对象差异核对

| 对象 | 云端 | 本地 | 影响判断 |
|---|---:|---:|---|
| PostgreSQL | 17.6 | 17.6 | 一致。 |
| `vector` | 0.8.0 | 0.8.2 | 现有向量列、距离查询和扩展均可用；小版本差异未表现为迁移错误。后续向量索引/升级前应在本地验证执行计划与结果。 |
| `pg_net` | 不存在 | 0.20.3 | 自建 Supabase 默认扩展；当前 InsightPro 代码未调用 `net.http_*`，暂未发现影响。 |
| 触发器（auth/public/realtime/storage/vault） | 5 | 9 | public 业务表均无差异；多出的 4 个在 Storage schema，是本地 Storage 版本初始化对象。当前无 Storage object、无 InsightPro Storage API 调用。 |
| 约束（auth/public/realtime/storage/vault） | 236 | 253 | auth/public/vault 数量一致；差异落在 Realtime/Storage 内部 schema（local realtime +10、storage +7）。当前业务表约束未变。 |
| Index（auth/public/realtime/storage/vault） | 266 | 277 | public 127 个一致。云端额外有 4 个 Auth users 查询索引；Storage 的 `(bucket_id,name)` 唯一索引云端存在、本地缺失；本地多出 Realtime 分区索引与 Storage 内部索引。当前没有 Storage 对象或 Realtime 订阅，因此未阻塞当前业务；若启用 Storage，应先核验/补齐唯一性与冲突行为。 |
| `realtime.schema_migrations` | 82 | 91 | 本地 Realtime 组件迁移账本较新；未手工改写账本。当前应用代码未使用 Realtime channel。 |
| `storage.migrations` | 68 | 75 | 本地 Storage 组件迁移账本较新；未手工改写账本。当前 Storage 对象数为 0，应用代码未使用 Storage SDK。 |
| RLS policy | 0 | 0 | 数量一致；`email_subscribers` RLS 未启用，API 权限来自后端管理员校验。 |
| Auth 用户 | 5 | 5 | 账户字段和密码哈希指纹一致；已通过本地代理登录并由后端校验 token。 |

系统对象有版本差异，不能据此声称整套 Supabase 内部 Schema 字节级一致。迁移没有擅自修复索引或 migration ledger。建议数据治理阶段把缺失的 Auth/Storage 索引和 Realtime/Storage 账本差异作为独立兼容性检查项，不直接执行 `stamp`、migration repair 或历史数据修复。

## 验收状态

- 前端 `/supabase` Auth 代理登录：通过。
- 后端管理员鉴权、数据库读取：通过。
- Event 列表、Event 详情和 Evidence 读取：通过。
- 前端代理 → 后端业务写入、读回、软删除：通过；测试数据清除。
- 数据库事务 INSERT/UPDATE/SELECT/ROLLBACK：通过；回滚后零残留。
- Agent SSO 单元测试：9 passed；真实 Gateway SSO 端到端尚未执行。
- 后端启动 Alembic/运行时 DDL：通过 `STARTUP_SCHEMA_ENABLED=false` 禁用；调度已恢复，启动补采关闭。
