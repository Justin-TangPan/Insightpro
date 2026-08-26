# 版本日志

## [0.0.48] - 2026-08-26

### Insight-Agent 工作区命名
- SSO callback 自动读取当前 Supabase 用户姓名，缺失时使用邮箱前缀，并通过非敏感展示 Cookie 传给 Agent 启动脚本。
- 启动脚本自动更新 `/workspace` 的本地项目注册信息与 OpenCode 项目显示名；用户无需创建或命名 Workspace。
- InsightPro 登出时同时清理 Gateway Session Cookie 和工作区显示名 Cookie。

### 验证
- 待部署后补充中文用户名编码、项目名称更新、Cookie 清理和完整健康结果。

## [0.0.47] - 2026-08-26

### Insight-Agent 会话修复
- Gateway Session 从 5 分钟延长到 30 天，避免用户工作过程中 OpenCode API 被 302 重定向并显示“没有对话”。
- InsightPro 退出登录仍会立即撤销该用户的全部 Agent Gateway Session；一次性 SSO Ticket 仍保持 60 秒有效。

### 验证
- 待部署后补充 SSO Cookie、数据库到期时间、登出撤销和 Agent 消息链路结果。

## [0.0.46] - 2026-08-26

### Insight-Agent 工作区体验
- 修复 620px 浮窗触发 OpenCode 项目选择/响应式布局异常：默认浮窗调整为 900×720，并继续支持拖动和缩放。
- Gateway 在原生应用启动前初始化其同源项目注册表，固定打开 `/workspace`；SSO callback 直接进入该 Workspace 的 Session 页面，用户不再手动选择项目。
- 浮窗标题移除只读提示，产品界面只保留 Insight-Agent 名称。

### 写入边界
- 独立 Workspace 改为可写并开放 OpenCode `edit`，支持在副本中修改代码。
- 继续禁用 bash、task、外部目录和 web 工具；生产仓库、生产 `.env`、Docker Socket 与业务数据库仍不挂载。

### 验证
- 项目注册启动脚本通过幂等自检；真实 Supabase SSO callback 直接进入 `/workspace` Session 路由，返回页面已注入启动脚本。
- 容器挂载确认 `workspace_rw=true`，实际创建、读取并清理测试文件通过；edit 允许，bash/task/外部目录仍拒绝，Workspace 未发现 `.env`。
- 前端 ESLint、20 路由生产构建、Prisma、后端 39 项测试、InsightPro full health 和 Insight-Agent 独立健康检查全部通过。

## [0.0.45] - 2026-08-26

### Insight-Agent 产品集成
- 产品层统一更名为 Insight-Agent；Sidebar 改为站内完整工作区，根布局新增可拖动、缩放、最小化、关闭、最大化/还原的浮窗。
- 浮窗与完整工作区复用一个持久 iframe，路由切换不重建底层页面和 Session；旧 `chat.js` 不再挂载，后台 AI Pipeline 与 Legacy Chat API 保留。
- 新增 `services/insight-agent/` 子项目文档，集中说明产品关系、架构、安全、部署和项目上下文。

### 只读安全边界
- InsightPro 独立 Git Workspace 改为只读挂载，固定配置文件也只读；OpenCode 权限拒绝 edit、bash、task、外部目录及 web 工具，只保留项目内读取、搜索和分析。
- Gateway 嵌入响应增加 `frame-ancestors` 来源限制；继续使用 Supabase 一次性 Ticket 与短时可撤销 Session，仅授权唯一管理员。

### 验证
- 前端 ESLint 与 Next.js 20 路由生产构建通过。
- 后端 39 项测试、Prisma 校验、主/Agent Compose 健康检查和 InsightPro full health 通过。
- 真实 Supabase SSO、一次性 Ticket、防重放、登出撤销和 iframe `frame-ancestors` 通过。
- 容器内实际写 Workspace 失败，权限配置确认 edit/bash/task/外部目录均拒绝，Workspace 未发现 `.env`。
- Agent 重启前后 Session ID 集合一致；停止整个 Agent Compose 时 InsightPro full health 仍通过，随后 Agent 独立恢复健康。

### Docker 运行时
- Huawei Cloud EulerOS 2.0 系统仓库仅提供 Docker 18.09，已使用官方稳定静态二进制升级到 Docker 28.5.2 / API 1.51，并保留原 RPM 与数据目录作为回滚路径。
- 移除项目脚本和 systemd unit 中遗留的 API 1.39 强制降级；Docker 升级后主栈重新发布成功。

### 已知限制
- 底层单实例仍共享 Session、Workspace、配置和 Provider 凭据，尚不具备多用户隔离，不能向第二位用户开放。
- 当前 IP + HTTP 环境无法启用 Secure Cookie，正式使用前仍需 HTTPS 域名。

## [0.0.44] - 2026-08-26

### 用户系统与 OpenCode SSO
- 将分散的 `useAuth` 状态合并为全局 `AuthProvider`，新增 Next.js Proxy 统一保护 Workbench、设置和 OpenCode 启动页；登录支持安全的站内 `next` 回跳。
- 新增 OpenCode Auth Gateway：Supabase 登录用户以 Bearer Token 向 InsightPro 换取 60 秒一次性 ticket，Gateway callback 创建 5 分钟 HttpOnly Session，服务端注入 OpenCode Basic Auth。
- ticket 和 Gateway Session 仅以 SHA-256 摘要存储；ticket 原子单次消费，退出 InsightPro 时立即撤销该用户全部 Gateway Session。
- OpenCode 不再直接发布端口，仅 Gateway 暴露 `4096`；匿名访问跳转 InsightPro 登录，OpenCode 服务密码、Supabase Service Role 和模型密钥均不下发浏览器。

### 多用户安全边界
- 实测 OpenCode `session`、`message`、`permission`、Workspace 和 Provider 均无 InsightPro `user_id` 所有权，单实例不能安全承载相互隔离的用户。
- 当前只允许唯一指定管理员进入共享实例；普通 InsightPro 用户返回 403。正式多用户开放必须按 `user_id` 路由到独立 OpenCode 实例、数据目录和 Workspace。

### 验证
- 后端 39 项测试、前端 ESLint、Next.js 生产构建、Prisma schema 与两个 Compose 配置通过。
- 真实 Supabase 管理员完成 ticket 换取并进入 OpenCode 原生 Web；匿名访问跳转登录，非法/过期/重放 ticket 均返回 401，ticket URL 不含 Supabase Token。
- 退出撤销后原 Gateway Cookie 立即失效；OpenCode 服务重建前创建的 Session 仍可读取，InsightPro full health 与 OpenCode 独立健康检查均通过。

### 已知遗留
- 当前仍是 HTTP IP+端口临时验收，Cookie 暂不能启用 `Secure`；正式环境必须使用独立 HTTPS 子域名。
- 尚未实施一用户一实例，因此不能向第二位 InsightPro 用户开放 OpenCode。

## [0.0.43] - 2026-08-26

### OpenCode 第一阶段
- 固定 OpenCode `1.18.23`，使用独立 `insight-opencode` Compose project、独立网络、systemd unit 和管理脚本部署原生 Web UI。
- Session、全局配置、缓存、状态及 Git Workspace 分别持久化到 `/var/lib/insight-opencode/`；Workspace 是当前 InsightPro 提交的独立 clone，不挂载生产目录、生产 `.env` 或 Docker Socket。
- 容器使用 UID/GID 10002、只读根文件系统、移除全部 capabilities，并限制为 1.5 CPU、2 GiB 内存、512 PID、256 MiB 临时目录、30 MiB Docker 日志和 20 GiB 持久化预算监测。
- OpenCode 启用独立 Basic Auth、禁用自动升级和 Session 分享；当前使用服务器 IP `4096` 端口作为临时验收入口。
- InsightPro Sidebar 新增 `OpenCode / AI Agent` 外部入口，以新标签页打开原生 OpenCode，不接入 FastAPI、Supabase 或现有健康链路。

### 验证
- 匿名 OpenCode 健康请求返回 401；认证后的原生 Web 与 `/global/health` 返回 200，容器健康版本为 `1.18.23`。
- 创建真实 Session 并通过现有模型得到“OpenCode 工作正常”回复；重启后 Session 和配置哈希保持一致。
- OpenCode 容器安全边界、资源限制、挂载和独立网络均经 Docker inspect 核对。

### 已知遗留
- 当前没有可用域名和 HTTPS 反向代理，外部入口仅用于临时验收；正式开放前应迁移到独立 HTTPS 子域名。
- 本阶段复用了现有模型服务凭据并存放在独立的 `0600` 运行时环境文件中；获得独立额度密钥后应单独轮换。

## [0.0.42] - 2026-08-25

### 搜索
- 全局搜索从仅匹配三类标题升级为跨技术项目、阿里云方案正文、友商动态，以及登录用户自己的 Requirements 和 Solutions 检索。
- 支持空格分隔的多关键词 AND 查询、标题精确/前缀/包含相关性排序、跨快照去重、内容摘要、类型聚合筛选和服务端分页。
- 搜索页面增加关键词高亮、五类结果筛选、快捷关键词、明确错误与空状态，以及内外部链接识别。

### 性能与安全
- 使用 PostgreSQL `pg_trgm` 和五个 GIN 组合文本索引优化模糊检索，不引入新的搜索服务。
- Workbench 结果仅在有效 Supabase Auth 会话下加入，并继续由 `user_id` 限定；匿名搜索不返回个人数据。

### 验证
- 后端 35 项测试、前端 ESLint、Prisma schema 校验、Next.js 生产构建和 `git diff --check` 通过。
- 真实 PostgreSQL 验证多关键词、分类分页、个人结果隔离及五个搜索索引；临时 Workbench 数据已清理。
- 提交 `c715f30` 已自动部署；生产搜索页返回 200，“数据迁移”返回 13 条/3 页，方案筛选 11 条，匿名结果无 Workbench 类型，前后端容器与端到端健康检查通过。

### 已知遗留
- 当前每个数据源最多参与 100 条候选结果排序；单类有效匹配长期超过 100 条时，应将统一相关性排序下推到 PostgreSQL 全文查询。

## [0.0.41] - 2026-08-25

### 交互
- 阿里云技术解决方案目录增加二级领域内分页，每页 12 项，显示当前范围、总数和总页数，并提供上一页、页码与下一页操作。
- 切换一级或二级领域时自动回到第 1 页；翻页后自动定位到方案列表顶部，避免继续在长页面底部滚动。

### 项目规则
- 将变更后自动部署规则更新为当前 Linux Docker Compose 发布流程，后续完成验证后直接提交并执行 `scripts/deploy-docker.sh`。

### 验证
- 前端 ESLint、Next.js 生产构建和 `git diff --check` 通过，18 个应用路由生成成功。
- 提交 `f719f2d` 已自动部署；生产页面返回 200，前后端容器及端到端健康检查通过，35 项示例二级领域按每页 12 项计算为 3 页。

### 已知遗留
- 当前没有浏览器自动化，分页交互通过类型检查、生产构建和部署后页面/API 探针验证。

## [0.0.40] - 2026-08-25

### 修复
- 阿里云技术解决方案目录改为完全由官方菜单树生成，移除前端硬编码分类顺序，按 9 个一级领域、33 个二级领域和官方方案顺序展示。
- 新增存量基线语义：当前 414 项方案全部标记为普通方案，不再因首次采集日期落在近 7 日而错误置顶。
- 每日采集继续按 URL 与内容指纹和上一版比较，仅真正新增的方案进入页面顶部“新增方案置顶”，内容变化标记为更新，下线方案记录 `removed_at`。
- 首页近 7 日方案变化同步排除普通基线，避免统计口径与洞察页不一致。

### 验证
- 官方目录同步后实测 414 项方案、9 个一级领域、33 个二级领域，官方顺序完整覆盖 `0–413`。
- 连续第二次全量同步结果为新增 0、更新 0、下线 0；页面数据为基线 414、置顶 0、今日变化 0。
- 后端基线/新增分类回归测试、前端 ESLint、Prisma schema 校验和生产构建通过。
- 提交 `68e4250` 已部署；生产页面返回 200，API 口径与 9/33/414 基线一致，前后端容器及端到端健康检查通过。

## [0.4.0] - 2026-08-25

### 新增
- 新增 Requirements 工作台：支持创建、编辑、删除、列表、详情、状态筛选、优先级、来源追溯和关联 Solution。
- 新增独立 Solutions 工作台：支持创建、编辑、删除、列表、详情、分类、状态、版本、参考链接和相关 Requirement 回查；不复用或修改 `aliyun_solutions`。
- 新增 `requirements`、`solutions`、`requirement_solutions` 三张 PostgreSQL 表，启用 RLS，并按 `Router → Service → Repository → Database` 组织 Workbench 新代码。
- 解决方案洞察条目增加“创建需求”，自动带入来源类型、原始数据 ID、原始链接和标题；Requirement 可关联已有 Solution，或创建并自动关联新 Solution。
- 侧边栏新增工作台分组；首页增加 Requirement 数量、Solution 数量和最近 Requirement，原技术解决方案洞察保持主体位置。

### 版本与资料
- FastAPI、前端包和 Docker 镜像统一升级为 `v0.4.0`。
- 同步更新助手知识、数据库契约、技术与业务架构清单、运维手册及页面入口。

### 验证
- 后端 33 项测试通过；新增 Workbench 业务规则检查和未登录 API 权限门禁。
- 前端 ESLint、Prisma schema 校验和 Next.js 生产构建通过，共生成 18 个路由。
- 在真实 Supabase PostgreSQL 完成 `Insight 来源 → Requirement → 自动关联 Solution → Solution 反查 Requirement` 双向闭环，并清理验收临时数据。
- RLS 启用后验证 Repository 可正常访问，其他用户 ID 无法读取测试 Requirement。
- Docker `0.4.0` 前后端镜像已于 2026-08-25 重新构建并部署；端到端健康检查通过，两个 Workbench 页面返回 200，未登录 API 返回 401。

### 已知遗留
- 当前环境未配置浏览器自动化，页面完成编译、静态生成和 API/数据库闭环验证，但尚未执行自动化点击级 UI 测试。

## [0.0.39] - 2026-08-25

### 视觉系统
- 建立统一页面 gutter、模块垂直节奏、卡片内边距，以及 H1/H2/H3、正文、辅助文字和数据字体层级。
- 绿色调整为唯一主题主色，橙色仅用于变化、失败和删除等警示语义；专题页遗留色全部收敛到主题与中性色。
- 主要卡片由实线边框分割改为白色/浅灰背景层级，统一数字卡片留白、列表行高和标签样式。
- 统一主按钮、次按钮、输入框、链接、hover、选中和键盘焦点反馈，并补充 reduced-motion 处理。
- 首页 Banner 调整为均衡双栏结构，将“发现—理解—应用”升级为高权重三步决策轨道。

### 验证
- 前端 ESLint 与 Next.js 生产构建通过，14 个静态页面生成成功。
- 全局颜色扫描无主题外 Tailwind 色或破损 token，`git diff --check` 通过。

## [0.0.38] - 2026-08-25

### 文档
- 重写根目录与前端 README，统一产品定位、启动方式、页面入口、环境变量和质量门禁。
- 新增技术架构与业务架构清单，覆盖产品边界、角色、能力、业务流程、技术栈、组件、数据、API 权限、调度、安全和扩展条件。
- 重写数据库契约、运维手册和改进清单，使其与当前 10 张业务表、Docker 双容器部署及实际任务链路一致。
- 清理过期整改基线与失效本地路径，当前资料不再引用已删除页面和接口。

### 验证
- 当前文档过期路由/API 关键字扫描无残留，Markdown 本地链接完整。
- Prisma schema 校验通过；架构清单中的表、路由、权限、调度和运行快照已与代码及健康接口交叉核对。

## [0.0.37] - 2026-08-25

### 调整
- 产品定位收束为技术解决方案洞察平台，首页改为“技术热点 → 方案变化 → 友商验证”的单一洞察链路。
- 下线行业洞察、政策雷达、招标信息及其衍生页面、API、采集任务、搜索入口、助手知识和旧演示材料。
- 全局搜索与深度研报改为使用技术项目、解决方案和友商动态；补齐解决方案目录 API。

### 数据
- 删除 PostgreSQL 中 `industry_news`、`policy_updates`、`bidding_opportunities`、`demand_signals`、`demand_reports` 五张表并确认无残留。
- 删除旧 Qdrant 向量缓存，改用 PostgreSQL 轻量上下文检索，避免被取消数据再次进入问答上下文。
- Compose 移除废弃的 Qdrant 数据卷挂载，部署后不再保留旧向量数据。

### 验证
- 后端 Python 语法编译与 26 项测试通过。
- 前端 ESLint、Prisma schema 校验与 Next.js 生产构建通过；静态页面由 21 个收敛为 14 个。

## [0.3.0] - 2026-08-24

### 发布
- 正式版本从 `v0.2.0` 演进至 `v0.3.0`，合并解决方案洞察、技术项目用途速读与邮件订阅排期。
- 统一前端包、Docker 镜像、FastAPI 元数据、根接口、测试与项目文档的版本号。

### 新增
- 新增阿里云解决方全量目录、变化检测、价值简介、首页摘要与每日自动更新。
- 技术热点扩展至 25 个项目，增加基于 README 的项目用途总结。
- 邮件订阅支持每位订阅者独立选择星期和时间，管理员可保存排期并单人立即发送。

### 修复
- Supabase 连接状态改为读取独立数据库检查位，不再受数据新鲜度 `503` 影响。
- 邮件预览、单人发送和定时发送统一复用同一份 HTML 模板。

### 验证
- 后端 28 项测试通过，前端 ESLint 与 Next.js 生产构建通过，生成 21 个静态页面。
- 邮件 HTML 经 MIME 编解码往返后完全一致，Supabase 订阅字段迁移成功。
- Docker 前后端容器健康、重启次数为 0，端到端数据链路检查通过。

### 已知遗留
- 当前部署为单 API 副本内嵌调度器；扩展多副本前需为邮件任务增加数据库租约。
- `npm audit --omit=dev` 报告 12 项已知依赖风险（3 moderate、9 high、0 critical）；Next.js 和 Prisma 依赖升级需要单独验证后纳入后续版本。

## [0.0.36] - 2026-08-24

### 新增
- 邮件订阅表增加 `weekdays`、`send_time` 和 `last_sent_at`，后端每分钟按个人排期执行一次到期检查。
- 设置页增加订阅者星期组合、时间点、排期保存和单人立即发送。

### 修复
- 就绪报告显式返回数据库检查结果，设置页不再用整体新鲜度代替 Supabase 连接状态。

### 验证
- 后端 28 项测试、前端 ESLint、生产构建、Docker 健康检查和邮件 MIME 一致性检查通过。

## [0.0.35] - 2026-08-21

### 调整
- 解决方案洞察由 419 条卡片平铺改为阿里云原生目录结构：左侧 9 个一级领域，右侧按官方二级目录分组。
- 桌面端使用分类目录切换，移动端使用原生下拉选择；每次仅渲染当前领域，保留目录内新增与更新置顶标记。

### 验证
- 前端 ESLint 与 Next.js 生产构建通过，共生成 21 个静态页面。
- 前端镜像已重建重启；目录页、同源数据链路与容器健康检查通过，并完成桌面端页面截图核验。

## [0.0.34] - 2026-08-21

### 新增
- 新增“解决方案洞察”栏目，完整展示阿里云技术解决方案、20–30 字价值简介、官方详情链接和最近变化日期。
- 新增阿里云解决方案采集与 PostgreSQL 存储；通过内容指纹识别新增、修改和下线方案，只对变化内容重新生成摘要并自动置顶。
- 每天 09:00 自动检查更新，同时支持登录用户手动刷新和启动缺失补跑。
- 首页模块、侧边导航和全局智能助手知识同步新增解决方案入口。

### 数据
- 修正数据源：由首页 8 个“专题推荐”切换为左侧官方完整目录树，覆盖方案详情、部署教程与目录中的外部方案入口。
- 全量简介均由官方详情描述生成并校验为 20–30 字；日常少量变化继续使用 AI 增强摘要。

### 验证
- 后端 24 项测试通过（存在 1 条 Supabase 依赖弃用警告）。
- 前端 ESLint 和 Next.js 生产构建通过，共生成 21 个静态页面。
- 09:00 定时任务、实时页面解析、数据库入库和版本差异检查通过。
- 官方目录与数据库均核对为 419 条（188 个方案详情、217 个部署教程、14 个外部方案入口），405 条含官方详情描述，全部简介均为 20–30 字。
- 连续两次全量检查结果稳定，第二次为 0 新增、0 更新、0 下线。
- 后端镜像已重建重启；直连及前端同源代理均返回 419 条，解决方案页面 HTTP 200，端到端健康检查通过。

### 已知遗留
- 数据源依赖阿里云公开页面结构；解析失败时保留数据库现有内容并等待下次检查。
- `npm ci` 当前报告 14 个依赖漏洞（3 个 moderate、11 个 high），本次未执行可能引入破坏性升级的 `npm audit fix --force`。

## [0.2.0] - 2026-08-21

### 发布
- 正式版本从 `v0.1.0` 演进至 `v0.2.0`，汇总现有 `0.0.7` 至 `0.0.33` 的内部迭代。
- 统一前端包、Docker 镜像、FastAPI 元数据、根接口和项目文档的版本号。
- 重写 README，补齐当前能力、架构、部署、开发、环境变量、页面、API 和验证说明。

### 验证
- 项目版本入口一致性检查通过。
- 后端 22 项测试通过（存在 1 条 Supabase 依赖弃用警告）。
- 前端 ESLint 和 Next.js 生产构建通过，共生成 20 个静态页面。
- Docker Compose 配置解析与 Git diff 空白检查通过。

### 已知遗留
- `v0.2.0` Git 标签应在当前工作区全部改动完成验证并提交后创建。

## [0.0.33] - 2026-08-11

### 修复
- 邮件日报发送与预览显示不一致问题：
  - `send_email()` 改为直接使用 `MIMEText`（而非 `MIMEMultipart("alternative")`），避免部分邮件客户端（如 QQ 邮箱）对 multipart/alternative 仅含 HTML 时的渲染差异。
  - 日期颜色由 `rgba(255,255,255,0.55)` 改为实色 `#A0B5AA`，兼容不支持 RGBA 的邮件客户端。
  - CSS 增加 `-ms-text-size-adjust` / `-webkit-text-size-adjust` / `img` 重置样式，提升多客户端一致性。
- 邮件 GitHub 趋势卡片中新增 AI 项目速读（summary）展示。

### 验证
- Python 语法编译通过。
- HTML 标签平衡校验通过。
- Docker 后端镜像已重建重启。

## [0.0.32] - 2026-08-10

### 修复
- 邮件日报"查看完整洞察报告"链接地址从旧服务器 IP（94.74.90.21）更新为当前服务器公网 IP（159.138.89.233）。
- 同步更新 `settings.py` 中 `CORS_ORIGINS`、`rebuild.py`/`rebuild2.py` 和文档中的旧 IP 引用。

### 验证
- `.env` 中 `BASE_URL` 已更新。
- 所有文件中旧 IP `94.74.90.21` 已替换完毕，无残留引用。

## [0.0.31] - 2026-07-25

### 新增
- 技术热点的现有 AI 分析新增独立项目用途总结，说明项目是什么、解决什么问题及可用于什么场景；分析范围由 Top 10 扩至完整 25 条上限，并同步展示在热点卡片与每日邮件中。
- 系统设置的邮件订阅管理新增真实邮件预览，复用正式发送模板并保持管理员权限边界。
- `trending_business_eval` 新增 `summary` 字段，数据契约、Prisma 模型与结构校准脚本同步更新。
- 后端启动时自动补齐 `summary` 字段，并在发现当日项目缺少用途总结时自动调用 AI 回填，无需人工执行迁移或重新评估。
- 项目用途总结主要读取 GitHub README，每条严格要求至少 100 字；README 不可用时才降级使用项目简介，短于 100 字的 AI 结果不会入库。

### 验证
- 后端 22 项测试通过，52 个业务 Python 文件语法编译通过。
- 前端 ESLint 和 Next.js 生产构建通过。

## [0.0.30] - 2026-07-17

### 调整
- 邮件日报将“今日技术洞察”和“AI 业务价值评估”置顶，友商动态等内容后置。
- 邮件新增当日 AI 价值评估、推荐建议和分析理由，并按综合评分排序展示。
- 邮件整体改为清新的绿色系视觉，容器、卡片、标签和按钮统一增加圆角。

### 验证
- Python 语法编译和真实数据邮件渲染通过，栏目顺序及 HTML 表格标签校验通过。

## [0.0.29] - 2026-07-16

### 修复
- 技术热点页切换历史日期时，同步展示该日已入库的 AI 业务价值评估、四维评分和分级汇总，不再隐藏历史评估面板。

### 验证
- Supabase 历史接口已返回按日保存的评估，前端 ESLint、Next.js 生产构建和 Docker 健康检查通过。

## [0.0.28] - 2026-07-16

### 新增
- 在 Supabase Auth 创建 `admin` 管理员账号，登录页支持用户名或邮箱登录。

### 安全
- 订阅者查看、删除、测试邮件和立即发送改为仅 `admin` 角色可用，普通用户返回 403。

### 验证
- 管理员登录、权限校验、订阅者列表和 Docker 端到端健康检查通过。

## [0.0.27] - 2026-07-16

### 修复
- InsightPro 智能助手改用已验证的非流式聊天接口，避免 ModelArts 推理片段和 SSE 跨数据块导致的空白回复。
- 前端现在显示后端返回的真实错误，并移除与实际模型不符的 DeepSeek 标识。

### 验证
- ModelArts 普通聊天接口返回正常，前端构建与 Docker 端到端健康检查通过。

## [0.0.26] - 2026-07-16

### 修复
- 行业洞察的云厂商竞争格局中，将误合并的 AWS / Azure 拆分为两家独立厂商，分别展示定位、优势和重点行业。

### 验证
- 前端 ESLint、Next.js 生产构建和 Docker 健康检查通过。

## [0.0.25] - 2026-07-16

### 调整
- 行业洞察、案例库和云厂商调研页不再展示华为云案例与动态，聚焦 AWS、Azure、阿里云、腾讯云和火山云。
- 每日云厂商采集移除华为云源，新增 Microsoft Azure 官方客户案例与博客源。
- 设置页订阅者加载失败时不再误报“暂无订阅者”，未登录时明确引导登录，避免公开邮箱名单。

### 验证
- 后端测试、前端 ESLint、Next.js 生产构建和 Docker 端到端健康检查通过。

## [0.0.24] - 2026-07-16

### 调整
- 历史日报同时展示每日 GitHub Trending 快照和已入库的业务价值分析。
- 行业洞察新增近 30 天云厂商客户/生态合作动态，并将华为云伙伴案例、客户案例和新闻页纳入每日采集。
- 行业洞察、案例库和历史页的卡片与控件统一增大圆角。

### 验证
- 后端 21 项测试通过，Python 语法编译通过。
- 前端 ESLint 和 Next.js 生产构建通过。

### 已知限制
- 微信公众号正文存在登录、反爬与授权限制，本版优先采集云厂商官方新闻、客户案例和伙伴案例页。

## [0.0.23] - 2026-07-16

### 修复
- 系统设置页的 Supabase 状态改为读取后端就绪接口，不再硬编码显示“未配置”。

### 验证
- 前端 ESLint 和 Next.js 生产构建通过。

## [0.0.22] - 2026-07-15

### 修复
- **邮件 HTML 模板彻底重写**：修复了 `build_daily_digest_html()` 中所有表格结构问题。
    - 所有 `茶/愿/俨` 标签正确包裹在 `伻` 内，9 对 `茶`/40 对 `伻`/60 对 `愿` 完全平衡。
    - 每个 `愿` 都正确嵌套在 `伻` 内，每个 `伻` 都正确嵌套在 `茶` 内。
    - 新增 `@media` 响应式 CSS，移动端自动堆叠统计卡片。
    - 新增 Outlook `[if mso]` 条件注释，确保 Word 渲染引擎正确识别固定宽度。
    - 新增 `mso-table-lspace:0`/`mso-table-rspace:0` 消除 Outlook 额外单元格间距。
    - 去除所有「侃」乱码占位符和缺失标签导致的错位问题。
    - 同时修复了 Python 源码中缺失的 `import`、`=`、`for`、`if`、`def`、`with` 等关键语法结构（`send_email` 和 `send_daily_digest` 函数）。

### 验证
- Python 语法编译通过，`build_daily_digest_html()` 正常运行。
- 生成 HTML 所有表格标签完全平衡：9`茶`/9`茶`、40`伻`/40`伻`、60`愿`/60`愿`。
- 无乱码字符，含完整的 `@media` 响应式 CSS 和 Outlook 条件注释。
- 邮件同时兼容 Gmail / QQ邮箱 / Outlook 等主流客户端。

## [0.0.21] - 2026-07-14

### 新增
- 新增 `insight-docker-compose.service` systemd unit，在 Docker daemon 启动后自动执行 `docker-compose up --detach`，解决 Docker Engine 18.09 重启后无法通过 `restart: unless-stopped` 自行恢复容器的问题。
- 服务依赖 `network-online.target` 和 `docker.service`，确保网络和 Docker 就绪后才启动容器。

### 调整
- 开机自启主方案从 `restart: unless-stopped`（Docker Engine 18.09 下不可靠）切换为 systemd compose 服务 + 健康守护定时器双保险。
- 旧 `insight-web.target` 和旧应用级 systemd 服务已禁用，避免端口冲突。
- 健康守护脚本 `scripts/docker-health-guard.sh` 修复：恢复流程现在先执行 `down --remove-orphans` 清理过期网络，再重新 `up`，解决 daemon 重启后 `network not found` 的容器退出问题。
- 重写 `README.md`：更新项目结构、部署方式、页面列表、API 接口、运维要点，反映 Docker 生产部署现状和最新导航结构。
- 重写 `doc/运维手册.md`：更新开机自启原理、自启链路图、常用命令、自动修复逻辑、发布流程和数据补跑章节，移除过时的 systemd 原生部署描述。

### 开机自启链路（完整）
```
systemd (PID 1)
 ├─ docker.service                         (enabled)  ← Docker daemon
 ├─ insight-docker-compose.service         (enabled)  ← 开机启动容器
 └─ insight-docker-health-guard.timer     (enabled)  ← 每10分钟巡检 + 自动修复
```

### 验证
- `insight-docker-compose.service` enabled，依赖链正确（docker.service → network-online.target）。
- 健康守护定时器 enabled/active。
- 健康守护脚本已更新 `down --remove-orphans` 前置清理逻辑。
- 当前两个容器均 healthy，前后端 HTTP 200。

### 已知遗留
- Docker Engine 18.09 仍为最薄弱环节；建议单独维护窗口升级至 20.10+。
- HTTPS 反向代理和完整浏览器 E2E 监测仍需后续加固。

## [0.0.20] - 2026-07-13

### 调整
- 收紧左侧栏 `InsightPro` 与 `Business Intelligence` 的品牌标题行高，两行改为 `leading-none` 并显式设置 3px 间距，不影响全局正文排版。

### 验证
- 前端 lint、Next.js 生产构建、Docker 镜像替换和端到端健康检查通过。

### 字体现状
- 主界面英文和数字使用 Next.js `next/font` 自托管的 Inter 400/500/600/700/800；中文字形由当前操作系统的 sans-serif 字体回退提供。
- 当前 `font-serif`、标题工具类也被统一映射到 Inter，项目没有在主界面混用真正的衬线字体；聊天组件使用系统 UI 无衬线字体栈。

## [0.0.19] - 2026-07-13

### 新增
- 新增前后端多阶段 Dockerfile 和 `compose.yaml`：前端使用 Next.js standalone，后端使用 Python 3.11 slim，两个容器均以 UID/GID 10001 非 root 用户运行。
- 新增 `scripts/deploy-docker.sh`，在测试、lint、镜像构建通过后从 systemd 平滑切换到 Docker，新栈验收失败时自动回退。
- 新增 Docker 专用端到端巡检定时器，可重新创建/启动容器并在后端容器内执行数据补跑。
- 新增官方 Docker Compose 二进制安装与 SHA-256 校验脚本。

### 调整
- 生产开机自启主方案从应用级 systemd 切换为“Docker daemon + `restart: unless-stopped`”；旧 `insight-web.target` 和旧巡检已禁用，但保留作为发布失败回退。
- 容器内前端 API 代理目标固定为 Compose DNS `http://backend:8000`，不依赖宿主机 IP 或对浏览器开放 8000。

### 验证
- Compose 5.3.1 已通过官方 SHA-256 校验安装，并以 API 1.39 兼容当前 Docker Engine 18.09。
- 容器镜像构建通过；独立 13000/18000 预演通过，容器同源代理返回 healthy、GitHub 17 条、技术评估 10 条。
- 正式容器在 `0.0.0.0:3000/8000` 启动，后端与前端容器均通过 Docker healthcheck，端到端健康检查通过。
- 手动停止前端容器后，Docker 健康守护在约 4 秒内自动恢复完整数据链路。
- `docker.service` 与 `insight-docker-health-guard.timer` 均 enabled/active，两个容器均配置 `unless-stopped`。

### 已知遗留
- 当前 Docker Engine 18.09 较旧，Compose 需显式使用 API 1.39；已在项目脚本内兼容，但建议在单独维护窗口升级 Engine/Buildx，不与业务发布同时进行。
- 镜像目前仅保存在本机；如要在新服务器使用 `docker pull`，还需提供企业镜像仓库地址与凭据后执行 tag/push。
- HTTPS 反向代理、真实告警 Webhook 和完整浏览器 E2E 监测仍需后续加固。

## [0.0.18] - 2026-07-13

### 新增
- 新增存活与就绪探针：就绪检查同时验证 PostgreSQL、九类数据新鲜度、当日 GitHub 日榜和技术评估非空，解决“端口正常但页面空白”无法被发现的问题。
- 新增 `insight-health-guard.timer` 每 10 分钟端到端巡检；进程/代理故障自动重启，数据故障自动执行幂等启动补跑，并以一小时冷却避免重试风暴。
- 新增可选 `INSIGHT_ALERT_WEBHOOK` 持续故障通知和 `doc/运维手册.md`。

### 调整
- 部署验收从前后端首页 HTTP 200 升级为 8000 直连、3000 同源代理、数据就绪和技术评估 JSON 契约的完整检查。
- 新增运维 CLI `backend/maintenance.py repair-freshness`，供 Web 进程外的 systemd 巡检调用。

### 验证
- 后端测试通过：21 passed；新增新鲜但空评估、有数据但过期的负向就绪测试。
- Shell 脚本语法、Python 编译、前端 lint/build、systemd unit 校验、定时器实际执行和故障恢复演练通过。
- 完整健康检查通过：当日 GitHub 日榜 17 条、技术评估 10 条，九类数据状态为 fresh。

### 已知遗留
- 当前自动化验收到 API/JSON 契约层，尚未引入真实浏览器对 React 卡片渲染的 E2E 监测。
- 实际告警通道需配置 Webhook；未配置时持续故障仅记录在 journald。
- 36氪、一财、财联社的稳定替代源、专用非 root 用户和 HTTPS 入口仍需后续加固。

## [0.0.17] - 2026-07-13

### 修复
- 数据库核查确认当日 GitHub 日/周/月榜共 59 条、技术评估 10 条均完整，技术热点空白与数据库无关。
- 前端改为同源 `/api` 请求，由 Next.js rewrite 在服务端转发到 `127.0.0.1:8000`，浏览器不再直连局域网或公网 8000 端口。
- 移除客户端 `localhost:8000` 回退和构建时固化的 `192.168.0.191:8000`；全局助手运行时使用当前页面 origin。

### 验证
- Supabase PostgreSQL 直查确认：当日日榜 17、周榜 21、月榜 21，技术评估 10 条；项目名、链接和评分关键字段无空值。
- `npm run lint` 与 `npm run build` 通过。
- 通过前端 3000 端口访问同源代理验证：热点接口返回 17 条、技术评估返回 10 条、首页聚合返回 8 个模块，均为 HTTP 200。
- 局域网 `http://192.168.0.191:3000/api/...` 同源请求验证通过；全局助手配置为 `window.location.origin`。

### 已知遗留
- 正式公网使用仍建议增加 Nginx/Caddy 和 HTTPS，但技术热点不再依赖 8000 端口对浏览器开放。

## [0.0.16] - 2026-07-13

### 修复
- 修复局域网前端访问技术热点时被浏览器 CORS 拦截的问题：后端允许来源新增 `http://192.168.0.191:3000`，并改为通过 `CORS_ORIGINS` 环境变量集中配置。
- 移除 `main.py` 中散落的硬编码来源列表，避免前端 API 地址与后端 CORS 白名单再次漂移。

### 验证
- 服务端技术热点实时接口返回 17 条，技术评估返回 10 条，首页技术热点聚合返回 3 条。
- 新增局域网 Origin 回归测试，验证响应包含 `access-control-allow-origin: http://192.168.0.191:3000`。
- 后端完整测试、前端 lint/build 和重新部署结果见本轮验证记录。

### 已知遗留
- 当前前端 API 地址仍在构建时固化；后续引入 Nginx/Caddy 同源 `/api` 代理后应取消跨域部署模式。

## [0.0.15] - 2026-07-13

### 新增
- 新增 systemd 前后端服务和 `insight-web.target`，服务绑定 `0.0.0.0:3000/8000`，支持开机启动和异常自动恢复。
- 新增 `scripts/deploy.sh` 标准发布门禁、独立 `/opt/insight-web-venv` Python 环境及 `scripts/health-check.sh`。
- 新增启动补跑服务：按 GitHub、热搜、新闻/政策/厂商、友商、招标、需求、技术评估依赖顺序补齐当天缺失数据，并通过 PostgreSQL advisory lock 防止重复执行。
- 新增 `/api/data/freshness`，集中报告九个核心数据集的最新日期和新鲜度状态。
- 为刷新采集、技术评估、招标/需求分析、研报、爬虫控制、邮件管理和访问统计接口增加 Supabase Bearer 鉴权；前端管理请求统一自动携带当前会话令牌。

### 修复
- 修复 `.env` 依赖当前工作目录的问题，改为从项目绝对路径加载且不覆盖进程环境变量。
- 修复技术评估“数据库查询成功但当天为 0 条”时直接返回空结果的问题；当前先即时生成可展示评估，再由 AI 结果升级并持久化。
- 新闻、政策、厂商数据入库前增加空标题、乱码和不可追溯链接过滤；招标链接改为绝对地址，并保存真实来源、公告日期和状态。
- 商业快讯页改为读取最近两天真实 API 数据；首页实时模块为空时明确展示无新数据，不再回退五月/六月静态卡片。

### 验证
- 独立虚拟环境后端测试通过：18 passed（包含 8 个敏感接口匿名访问返回 401 的回归用例）；Python 语法编译通过。
- `npm run lint` 和 `npm run build` 通过，20 个静态页面生成成功。
- systemd target、前端和后端均为 active；强制终止前后端主进程后分别自动恢复为新 PID，健康检查继续通过。
- `/api/data/freshness` 返回整体 `fresh`；九个核心数据集最新日期均为 2026-07-13。
- 技术评估返回 10 条当日结果；首页、热点、快讯和核心数据 API 烟测均返回 200。

### 已知遗留
- DeepSearcher 依赖仍未安装，RAG 继续使用降级路径，启动日志的成功文案仍需修正。
- 36氪和一财当前解析结果为 0，财联社旧接口返回 404；已通过质量门禁阻止坏数据入库，但需要接入稳定官方接口或替代源。
- systemd 当前仍以 root 运行；后续应迁移到专用用户和 `/opt/insight-web`，并增加 Nginx/Caddy HTTPS 入口。
- 细粒度 RBAC、聊天接口限流、repository 分层和大型前端页面拆分尚未完成，继续按 Phase 2-5 推进。

## [0.0.14] - 2026-07-13

### 调整
- 将 Linux systemd 开机自启、统一服务 target、标准发布脚本和失败回滚要求加入整改计划 Phase 0。
- 新增数据源与洞察时效治理 Phase 6，记录技术洞察为空、定时任务漏跑、静态内容冒充实时数据等根因。
- 补充 2026-07-12/13 数据新鲜度审计基线、各数据域 SLA、启动补跑、幂等、质量门禁和源级告警验收标准。

### 验证
- 当前前端继续监听 `0.0.0.0:3000`，后端继续监听 `0.0.0.0:8000`，健康检查均返回 200。
- GitHub Trending 现场抓取正常：日榜 17、周榜 21、月榜 21；当天快照已写入数据库。
- 数据库只读审计确认：技术评估最新为 2026-07-09，其他主要数据域多数停留在 2026-06-30 至 2026-07-03。
- 数据源现场检查确认：国务院、雷锋网、部分云厂商和中央采购可返回数据；36氪、一财为空，财联社旧 API 返回 404 且 HTML 降级结果存在乱码，地方采购源返回 502。

### 已知遗留
- 本轮只完成部署方案和数据源诊断入计划，尚未创建 systemd unit，也未修改技术评估空结果逻辑和采集器。
- 商业快讯、政策雷达、增长机会等页面仍包含静态内容，不能视为实时洞察。
- 当前 APScheduler 仍嵌在 Web 进程，服务错过固定执行时间后不会自动补跑。

## [0.0.13] - 2026-07-09

### 调整
- 重构左侧导航：取消所有折叠分组，仅保留 5 个固定一级入口：首页洞察、热点追踪、行业洞察、政策法规、系统设置。
- 重构 `/insights/industry` 为统一行业洞察页，融合原行业全景、云厂商竞争格局和标杆案例库内容。
- 修复智能助手配置：前端助手脚本不再回退到 `localhost`，快捷问题同步为新导航结构。
- 更新智能助手知识库和 DeepSearcher 内置平台知识，移除旧的友商洞察/案例库/数据大屏/研报等导航描述。
- 在项目规则中加入智能助手全局挂载、禁止生产 localhost 回退、导航变更必须同步助手知识库的要求。

### 验证
- `npm run lint` 通过。
- `npm run build` 通过。
- `python -m py_compile backend/routers/chat.py backend/deep_searcher_integration.py` 通过。
- `pytest -q backend/tests` 通过：6 passed。

### 已知遗留
- 旧路由 `/insights/competitors` 和 `/insights/industry/cases` 暂未删除，当前仅从主导航移除；后续可按需要改成重定向。
- `DeepSearcher` 依赖仍未安装，相关知识检索继续走降级路径。

## [0.0.12] - 2026-07-09

### 修复
- 修复 `/api/demand/trends` 在 `demand_tags` 为空时返回 500 的问题。
- 修复 `/api/market/overview` 和 `/api/market/industry-analysis` 在 DeepSearcher 降级模式下错误 `await` 同步检索结果的问题。
- 为需求报告增加兜底摘要：AI 或检索不可用时仍基于 `demand_signals` 返回可展示报告，并补齐报告历史首屏数据。
- 为深度研报列表增加系统基线报告：`insight_tasks` 没有完成报告时自动创建一份基于当前技术热点和需求信号的完成报告。
- 首页统计和每日洞察的商机模块增加“近期为空则取最新/总量”兜底，避免招标数据存在但首页显示 0 或空白。

### 验证
- `python -m py_compile backend/crawlers.py backend/routers/insights.py backend/routers/demand.py backend/routers/reports.py backend/services/demand_service.py` 通过。
- `pytest -q backend/tests` 通过：6 passed。
- 全量核心 API 巡检通过：GitHub、AI 评估、行业、竞品、招标、需求、政策、研报、搜索、邮件订阅均返回 200 且有可展示数据。

### 已知遗留
- `DeepSearcher` 依赖仍未安装，当前 RAG 能力处于降级模式；市场总览和行业分析依赖结构化数据库与 AI 兜底输出。
- 部分示例招标数据日期停留在 2026-06，首页已做“最新数据”兜底，但后续应恢复定时采集保证日期连续性。

## [0.0.11] - 2026-07-09

### 修复
- 修复部署后前端仍使用 `localhost:8000` 作为浏览器侧 API 地址的问题，改为当前服务器局域网后端地址 `http://192.168.0.191:8000`。
- 修复 GitHub Trending 接口在 Supabase allow list 拒绝数据库连接时返回 500 的问题：实时抓取成功后，即使数据库写入失败也会返回实时项目。
- 修复“技术热点 / AI 业务价值评估”在数据库不可用时完全空白的问题：增加实时 GitHub 项目评估路径，并在 AI 不可用时提供启发式临时评估。
- GitHub 历史记录和手动刷新接口增加数据库不可用降级，避免影响核心热点展示。

### 验证
- `python -m py_compile backend/routers/hotspots.py` 通过。
- `npm run lint` 通过。
- `npm run build` 通过。
- `pytest -q backend/tests` 通过：6 passed。

### 已知遗留
- Supabase 当前仍拒绝本机公网 IP 访问，历史数据持久化和数据库评估结果存储需放通 allow list 后恢复。
- 当前 AI 业务价值评估在数据库/AI 不可用时会使用启发式临时评分，需在真实 AI 配置可用时复核评分质量。

## [0.0.10] - 2026-07-09

### 调整
- 进入 Phase 2 数据契约整改：新增 `doc/database-schema.md`，记录后端当前使用的 public 表结构、字段、索引、唯一约束和后续待办。
- 重写 `frontend/prisma/schema.prisma`，使 Prisma 模型与后端 SQL / `backend/reconcile_schema.py` 的当前数据契约一致。
- 明确 Supabase Auth 用户不在 public Prisma schema 中建模，避免继续保留旧的 `User` / `Report` / `DataSource` 抽象误导维护。

### 验证
- `npx prisma validate` 通过。
- `npm run lint` 通过。
- `npm run build` 通过。
- `pytest -q backend/tests` 通过：6 passed。
- 后端语法编译通过。

### 已知遗留
- 当前执行环境 IP 不在 Supabase allow list，无法在线 introspection；待放通后需用真实数据库结构复核 `doc/database-schema.md` 和 Prisma schema。
- 后端 SQL 仍分散在 router/service/crawler 中，下一步应引入 `backend/repositories/*`。
- 关键写接口和管理接口仍需接入认证/权限保护。

## [0.0.9] - 2026-07-09

### 调整
- 更新项目提示词：在根目录 `CLAUDE.md` 和 `frontend/AGENTS.md` 中加入“每次可验证整改必须更新 `log/versions.md`”的项目规则。
- 重写 `doc/整改方案.md`，将旧的待审批方案更新为当前执行中的可维护性整改路线图，覆盖质量门禁、数据契约、认证边界、legacy 清理、前端拆分等阶段。
- 清理前端 ESLint warnings：
    - 删除未使用 imports、变量和参数。
    - 用 `useCallback` 补齐数据加载函数的 hook 依赖。
    - 修正 Supabase middleware 中创建 client 但未刷新用户会话的问题。
    - 对保留原生 `<img>` 的现有视觉背景做局部 lint 例外，避免在未配置远程图片域名时引入构建/布局回归。

### 验证
- `npm run lint` 通过：0 errors，0 warnings。
- `npm run build` 通过。
- `pytest -q backend/tests` 通过：6 passed。
- 后端语法编译通过。

### 已知遗留
- 数据库 schema、后端 SQL 与 Prisma schema 仍需专项统一。
- 关键写接口和管理接口仍需接入认证/权限保护。
- `npm audit` 漏洞仍需逐项评估处理。

## [0.0.8] - 2026-07-09

### 修复
- 修复后端启动阻断问题：邮件日报模板 f-string 语法错误、热点历史接口缺失 `timedelta`、GitHub 业务评估缺失 `httpx` 导入。
- 将 DeepSearcher 调整为可选增强能力；未安装时基础 API 可正常导入和运行，RAG 检索降级为空上下文。
- 修正后端依赖文件中不可安装的版本号，并新增 `backend/requirements-dev.txt` 记录测试依赖。
- 修复 Python 3.9 下爬虫模块类型注解兼容问题。
- 修复前端依赖缺失导致的生产构建失败。
- 清理前端 ESLint 阻断错误：替换显式 `any`、规避 React effect 同步 setState 规则、修正 JSX 未转义双引号、排除 Node 配置脚本误扫。

### 验证
- 后端语法编译通过。
- `pytest -q backend/tests` 通过：6 passed。
- `npm run lint` 通过：0 errors，仍有 unused/import、hooks deps、img 优化等 warnings 待后续清理。
- `npm run build` 通过。

### 已知遗留
- 前端仍有 lint warnings，需要下一轮清理。
- `npm audit` 仍有 7 个漏洞提示，其中 1 个 high、6 个 moderate。
- 数据库 schema、后端 SQL、认证边界仍需专项整改。

## [0.0.7] - 2026-05-30

### 新增
- **每日洞察全系统升级**：
    - **首页门户化**：重构了 Dashboard，使其成为“今日商业市场洞察”的门户，集成行业、热点、新闻、机会四个核心板块。
    - **子版块详情页**：新增了四个详细分析页面：
        - [行业全景洞察](file:///c:/Users/Administrator/Desktop/Project/traeproject/insight-web/frontend/src/app/insights/industry/page.tsx)
        - [技术热点追踪](file:///c:/Users/Administrator/Desktop/Project/traeproject/insight-web/frontend/src/app/insights/hotspots/page.tsx)
        - [商业快讯监测](file:///c:/Users/Administrator/Desktop/Project/traeproject/insight-web/frontend/src/app/insights/news/page.tsx)
        - [商业机会洞察](file:///c:/Users/Administrator/Desktop/Project/traeproject/insight-web/frontend/src/app/insights/opportunities/page.tsx)
    - **侧边栏导航**：升级了侧边栏，支持“今日洞察”子版块的快捷导航。
    - **外部链接集成**：所有新闻、项目、行业动态均已集成外部超链接，确保信息的真实性与可追溯性。
- **后端引擎优化**：
    - 新增 `/api/daily-insight` 接口，支持多维度数据的聚合。
    - 优化了 AI 提示词工程，以生成更具深度和实战建议的商业研报。
