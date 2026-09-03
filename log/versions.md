# 版本日志

## [0.8.24] - 2026-09-03

- 云方案 AI 摘要改为每 20 条分批处理，批量导入不再因总数超过 20 条整体退化为截断摘要。
- Readiness 增加阿里云与华为云当天有效方案非空检查，持续暴露数据库和数据新鲜度问题。
- 新增全局页面加载 Skeleton 与错误恢复边界。
- 后端版本改为 `APP_VERSION` 统一配置，前后端镜像同步为 `0.8.24`。
- 验证：后端测试 `84 passed`；前端测试 `4 passed`、生产构建通过；Lint 仅保留既有 Settings Hook warning。

## [0.8.23] - 2026-09-03

- 产品主线收敛为“技术雷达 → 方案实践 → AI 工作区”。
- 首页 Banner、洞察区和工作台入口改为围绕方案实践的单一路径。
- 主导航调整为技术雷达、技术热点、云厂商方案、方案实践、AI 工作区。
- 首页数据模块显示更新时间和空数据状态，避免空列表被误认为正常数据。
- 验证：前端生产构建通过、后端 API 测试 `28 passed`。

## [0.8.22] - 2026-09-03

- 将 AI 模型选择器从“更多”菜单提升到对话头部，用户可直接看到并切换当前模型。
- 切换后下一条消息立即使用所选模型。
- 验证：前端生产构建通过；Lint 仅保留既有 Settings Hook warning。

## [0.8.21] - 2026-09-03

- 修复自由讨论模型建议失败时仍显示泛化文案的问题，降级建议现在绑定当前页面或业务对象标题。
- 切换会话时同步刷新降级建议，避免沿用上一条会话的提示词。
- 验证：后端相关测试 `24 passed`、前端生产构建通过。

## [0.8.20] - 2026-09-03

- 自由讨论新增上下文建议接口：将页面标题、路径和业务上下文交给当前配置模型生成具体可点击问题。
- 模型建议不可用时保留按页面类型的本地降级文案，避免入口空白。
- 记录建议生成的模型 Token 用量。
- 验证：后端相关测试 `24 passed`、前端生产构建通过。

## [0.8.19] - 2026-09-03

- 自动推荐提示词改为按任务类型、工作阶段和对话轮次动态切换，避免所有会话重复同一组建议。
- 自由聊天入口根据当前页面（技术热点、方案、工作台或普通页面）提供不同起始问题。
- 验证：前端测试 `4 passed`、生产构建通过。

## [0.8.18] - 2026-09-03

- 顶部仓库入口改用标准 GitHub Mark 内联 SVG，移除不准确的 GitFork 图标。
- 验证：前端测试和生产构建通过。

## [0.8.17] - 2026-09-03

- 顶部栏右侧新增 GitHub 仓库快捷入口，支持新窗口打开并提供无障碍标签。
- 验证：前端测试 `4 passed`、生产构建通过。

## [0.8.16] - 2026-09-03

- 启动 InsightPro 全局视觉重设计：建立 Quiet Intelligence 中性画布、语义色彩、低噪声边框和统一卡片层级。
- 修复折叠侧栏与主内容宽度不同步；统一顶部栏、页面标题容器和侧栏选中态。
- 增加全局 `prefers-reduced-motion` 兜底，改善响应式与可访问性基础。
- 验证：前端测试 `4 passed`，Next.js 生产构建通过。

## [0.8.15] - 2026-09-03

- 修复 AI 用量统计漏记：流式请求开始即创建记录，完成或取消时更新 Token。
- MaaS 流式请求显式启用 `stream_options.include_usage`，兼容 OpenAI 与 Provider Token 字段命名。
- 验证：后端测试 `82 passed`；前端测试、生产构建和部署健康检查通过。

## [0.8.14] - 2026-09-03

- 流式回答空状态增加真实旋转加载指示和无障碍状态播报，发送区域标记忙碌状态。
- 增加页面焦点滚动预留，避免键盘焦点被固定头部遮挡。
- 验证：前端单元测试 `4 passed`、Next.js 生产构建通过；Settings 页保留既有 1 条 Hook lint warning。

## [0.8.13] - 2026-09-03

- Agent 删除、会话历史和文件成果弹窗统一复用 AppDialog/ConfirmDialog，统一 Esc、焦点回收和关闭路径。
- AI 工作室弹窗移动端滚动区域与键盘交互更一致。
- 验证：前端单元测试 `4 passed`、Next.js 生产构建通过；Settings 页保留既有 1 条 Hook lint warning。

## [0.8.12] - 2026-09-03

- AI 工作台更名为“AI 工作室”；将文件与成果置为对话头部和会话侧栏的直接入口。
- 上下文明确展示为已绑定的工作基线；预置任务改为可选的“推荐工作配方”，与自由问询保持边界。
- 浮窗取消 360px 强制最小宽度，小尺寸窗口隐藏分屏控制；紧凑工具栏改用统一可点击目标。
- 验证：前端单元测试 `4 passed`、Next.js 生产构建通过；Settings 页保留既有 1 条 Hook lint warning。

## [0.8.11] - 2026-09-03

- 方案实践的预置任务与提示词以已保存背景和关联材料为工作基线，明确事实、假设、缺口与待确认项。

## [0.8.10] - 2026-09-03

- 修复方案实践表单任意点击会触发 AI 背景校对的问题。
- 管理员可管理 AI API 地址、默认模型和模型白名单，并查看本系统记录的请求与 Token 用量；密钥仅保留在部署环境中。

## [0.8.9] - 2026-09-03

- 修复 AI 填充等待时的加载指示器被全局动效偏好静态化的问题。

## [0.8.8] - 2026-09-03

### AI 填充代理稳定性
- `/api/agent/practice-background` 改为专用 Next Route Handler，保留用户 Authorization 并允许 110 秒模型生成，避免 rewrite 代理提前断开 socket。
- 模型 Provider 异常统一返回可读的 502 响应，前端可以直接重试。

## [0.8.7] - 2026-09-03

### 方案实践 AI 填充校对
- AI 填充改为先生成独立草稿，并提供原文与结果对比；只有用户采用后才更新表单，仍需点击保存才会落库。
- 读取公开 GitHub 资料与普通生成使用明确等待文案；取消会中止请求，失败可保留原文重试。
- 复用全局 Dialog 与 Toast，补充安全 GitHub 仓库链接识别测试。

### 全局交互收口
- 新增可防连点的 ActionButton、原生 Dialog/ConfirmDialog、Toast、Tooltip 与类型化 Agent 事件；移除全站 `window.confirm()`。
- AI 小窗支持会话抽屉、更多菜单、停止生成、失败重试、复制、保存成果和阅读时不强制跳到底部。
- 报告创建与邮件预览也接入统一 Dialog，删除类操作采用一致的确认与焦点行为。

### 验证
- 前端单元测试 `4 passed`，ESLint `0 errors`，Next.js 16.2.6 生产构建通过。
- 保留 Settings 页面既有 1 条 ESLint Hook warning。

## [0.8.6] - 2026-09-02

### AI 填充输出修复
- 方案实践 AI 填充会在服务端白名单读取公开 GitHub 仓库 README，不再要求模型自行调用网页工具。
- 强制只返回最终 Markdown；检测到工具调用协议时自动纠正重试，持续异常则拒绝填入表单。
- 验证：GitHub URL 白名单与工具标记测试、Agent 专项测试通过。

## [0.8.5] - 2026-09-02

### SAC 插件与 AI 会话闭环
- SAC 插件固定上游 `workflows@cd765e5`，按任务选择加载 5 个核心 Skill、6 个 Workflow、3 个 Schema 与质量检查脚本；未选择的技能不会污染上下文。
- 预置任务仅在用户发送对应的默认任务文本时注入，深入研究中的自由问询不再执行原定任务。
- AI 小窗按用户仅提示首次、2 秒自动收起；当前页可见正文与用户隔离的方案实践背景会注入新会话。
- 切换、新建、关闭小窗及离开 AI 工作区时清理未问询的空会话；工作文件继续支持预览和鉴权下载。

### 验证
- 后端测试 `80 passed`；SAC quality runner CLI、Python 编译、JSON Schema 与 diff 检查通过。
- 前端单元测试、ESLint（0 errors）和 Next.js 生产构建通过。

## [0.8.4] - 2026-09-02

### AI 工作体验与 SAC 任务
- AI 小窗首次登录提示显示 2 秒后自动关闭并记录为已提示；方案实践可由用户点击“AI 填充”生成可编辑背景信息。
- 方案实践的“进入 AI 分析”任务改为“做成解决方案实践”，加载已启用的 SAC 技能与 Architecture Contract 门禁；预置任务不再覆盖用户本轮自由提问。
- AI 空间提供基于 `CHAT_MODELS` 白名单的模型切换；当前部署启用 openPangu Flash 与 GLM-5.2。

## [0.8.3] - 2026-09-02

### 方案实践闭环与文件交付
- 将 Requirement 兼容数据收敛到“方案实践”，历史未关联需求会幂等吸收为方案实践，并作为 AI 工作区背景上下文。
- Agent 支持以文件代码块生成文本工作文件；对话内可预览、按真实文件名下载，下载继续执行用户隔离校验。
- 工作台仅保留“方案实践”用户路径，旧需求入口重定向兼容一个版本。

## [0.8.2] - 2026-09-02

### 方案实践与文件输出
- 将工作台中的 Solution 收敛为用户可见的“方案实践”：背景信息及关联 Requirement 材料会在进入 AI 分析时自动注入当前 Context。
- Agent Artifact 现支持工作文件列表、Markdown 预览和下载；下载接口仍按用户身份校验。
- 验证：62 项后端测试、前端 lint 与生产构建通过。

## [0.8.1] - 2026-09-01

### Solution Engineering 长期上下文
- 新增 Insight-Agent 公共规则、解决方案实践背景、Solution Engineering Workflow、Solution Architect 角色与公共知识说明，并由 Native Runtime 按固定顺序加载。
- 每次会话额外注入默认角色、按 Task 推导的工作阶段、当前 Task、期望输出与现有 Context Bridge 对象快照；UI 在“当前上下文”中显式展示角色和阶段。
- 稳定知识不包含具体业务对象或凭据；Requirement、Solution、Insight 数据仍只来自用户隔离的动态 Context。

## [0.8.0] - 2026-09-01

### Insight-Agent Native Runtime（迁移第一阶段）
- Agent 对话默认改由 InsightPro 自己的 Runtime 执行：直接使用现有 OpenAI 兼容模型流，而不再经 Hermes CLI、Dashboard 和 stdout 解析。
- Task、显式 Context、会话历史、Markdown 输出与 Artifact 仍由 InsightPro 作为唯一业务事实源；模型只接收经过 Context Bridge 过滤后的当前用户数据。
- 原生模型 token 直接以 SSE 传递至前端，解决 Hermes CLI 无法安全提供真实 token 流的问题。
- Hermes 已从 Agent 对话、Session 删除和草稿导入链路移除；Insight-Agent Native Runtime 是唯一执行器。
- 主 Compose 不再挂载 Hermes Gateway Secret，也不要求 Hermes URL；Hermes 容器与 Gateway 已停止并移除，历史持久化目录保留以避免误删。

## [0.7.1] - 2026-09-01

### Hermes 执行与上下文
- 修复 Hermes CLI 未向 stdout 输出、但已持久化正式回答时被误判为执行失败的问题；Runtime 以 Hermes Session 的正式 assistant 内容为准。
- 修复 Context Bridge 文件的工作区归属权限，Agent 现在可读取当前对象的显式上下文，而不是退回公共数据猜测对象。
- 回答以安全的段流方式送达前端；不转发 Hermes CLI 的内部 Reasoning、扫描提示或工具过程。
- SSE 明确关闭中间层缓冲，并在正式回答开始时发送“正在输出回答”状态；回答按 48 字符稳定增量渲染，避免完整文本一次性跳出。

### 主题与交互
- 将 Agent 抽屉、输入框、代码块、品牌阴影、滚动条和加载态全部改为主题令牌；黑白、橙、蓝、紫切换会同步影响面板层次与交互反馈。
- 补齐按钮、选择框、输入框的柔和过渡与主题焦点态。
- 数据大屏的图表、图例、坐标轴和浮层改为主题令牌；移除未挂载的旧 DeepSeek 问答浮窗，避免留下另一套不受主题控制的聊天界面。
- 修复“经典绿”主题之前错误落到蓝色默认值的问题；五个主题均有独立的主色、表面、边框、图表和代码色。
- 修复 Tailwind `@theme inline` 将主题工具类构建期固化为蓝色的问题；`bg-primary`、`text-primary`、`border-primary` 等现改为读取用户当前主题变量。

## [0.7.0] - 2026-09-01

### 统一 AI 工作台
- 新增 `/workbench` 统一入口，聚合当前用户的 Requirement、Solution、Agent Session 与 Artifact，并按“需求 → 方案 → AI 工作 → 工作文件 → 成果”展示工作链。
- 左侧一级导航合并 Requirements、Solutions 与 Insight-Agent，仅保留“AI 工作台”；原列表和详情页作为工作台内部页面继续复用。
- 新增工作台内部导航：概览、需求、方案、AI 工作/文件/成果；快速动作会绑定最近的真实 Requirement 或 Solution。
- AI 全屏入口迁移至 `/workbench/ai`，旧 `/insight-agent` 自动跳转兼容；最近 AI 工作可直接恢复指定 Session。
- 用户侧统一使用“AI 工作台”“工作文件”命名，底层 Hermes Workspace 与隔离策略保持不变。

### 验证
- 前端 ESLint 0 errors（保留既有 Settings Hook warning），Next.js 生产构建和 TypeScript 检查通过。

## [0.6.12] - 2026-09-01

### 主题与 Agent 等待态
- 将对话发送时的“正在连接 Hermes Agent”改为准确的“正在生成回答”，避免把已启动 Runtime 误显示为连接等待。
- 为黑白、暖橙、商务蓝和科技紫补齐语义化卡片、面板、边框、警示和玻璃面板变量；固定 `bg-white` 面板会跟随当前主题表面色。
- 渐变 Banner、卡片悬停态和玻璃容器改为使用主题色混合，主题切换不再只改变页面底色。

## [0.6.11] - 2026-09-01

### 华为云目录校正
- 华为云复合分类“运维监控,AI”归一为 AI，修复分类文字误拼入方案 URL 的采集问题。
- “新增方案置顶”改为仅展示当日首次确认且非基线的方案；目录内历史补录统一标记为“近期收录”，不再声称新增置顶。
- 经华为云官方页面核实，DBSyncer 与轻量级多云管理平台是 2024 年既有方案，不属于本次新增。

### 左侧导航
- 系统设置与平台管理移至 AI 工作区之后的底部“系统管理”分组；平台管理仍仅管理员可见。

### 验证
- 后端相关测试 13 passed；前端 ESLint 0 errors（保留既有 warning），生产构建通过。

## [0.6.10] - 2026-09-01

### Agent Home 对象推荐
- “深度调研”自动绑定当前技术热点，“方案分析”自动绑定 Solution Intelligence，“开始实现”自动绑定当前用户的 Managed Solution。
- 快捷任务卡片显示实际对象名称，点击后直接经过 Agent Routing 创建带 Context 的 Session；没有对象时禁用并提示来源缺失。

## [0.6.9] - 2026-09-01

### 对话删除确认
- 对话删除由浏览器原生 `confirm` 改为 Insight-Agent 内置确认浮层，显示会话名称、不可撤销说明、取消和删除中状态。
- 点击遮罩可取消；删除请求失败时保留浮层并在 Agent 内显示错误。

## [0.6.8] - 2026-09-01

### Hermes 输出净化
- Runtime Manager 改为读取 Hermes Session 最后一条正式 assistant content，避免 CLI 的安全扫描提示、内部 Reasoning 和工具过程进入用户对话。
- Session API 不可用时仍保留 CLI 最终输出作为降级，不影响回答可用性。

## [0.6.7] - 2026-09-01

### Agent 卡住修复
- Hermes 完成回答后的 Session 回查增加 3 秒超时和降级处理，不再因辅助查询阻塞回答返回。
- 对话流每 10 秒返回 Hermes 的真实执行时长；执行异常会明确结束并提示重试，不再永久停留在“Agent 正在工作”。

### 验证
- 后端相关测试：30 passed；Runtime Manager 与 Python 语法检查通过。
- 前端 ESLint：0 errors，保留既有 Settings Hook warning；Next.js 生产构建通过。

## [0.6.6] - 2026-09-01

### Hermes Agent 统一执行
- Insight-Agent 交互式消息不再调用普通 `ai_service`，改为经受认证的 Runtime Manager 进入当前用户隔离 Workspace 中的 Hermes Agent 命名 Session。
- 新增服务端 Hermes Chat 适配端点，限制消息和输出大小、执行预算及用户身份；未启用危险操作自动批准。
- 建立 InsightPro Session 与 Hermes Session 映射；删除对话时先删除所属 Hermes Session，再删除业务映射。
- 完成真实 Provider 调用、Session 映射和删除验证。

### OpenCode 遗留清理
- SSO 服务、Repository、API 路由、Cookie、环境变量和数据库表统一迁移为 Agent/Hermes 命名。
- 已部署 SSO 表采用原地重命名保留数据；删除宿主机旧 `/etc/insight-opencode` 配置目录。

### Markdown
- Agent 回答使用安全的 GFM Markdown 渲染，支持标题、列表、表格、引用、链接、行内代码和代码块；原始 HTML 不执行。

### 验证
- 后端测试：57 passed。
- 前端 ESLint：0 errors，保留既有 Settings Hook warning；Next.js 生产构建通过。
- Hermes Runtime、Gateway、InsightPro 前后端健康检查通过。

### 当前限制
- Hermes CLI 适配层当前按完整回答返回，尚未提供逐 token 和结构化 Tool Event 流；前端 SSE 契约已保留，后续可替换为 Hermes JSON-RPC。

## [0.6.5] - 2026-08-31

### Insight-Agent 对话界面
- 重做完整工作区为对话优先布局：保留 InsightPro 主侧栏，Agent 内部提供最近对话、新对话、中央欢迎态、轻量任务引导和固定输入区。
- 会话历史增加所有者范围内的删除入口与二次确认；删除当前会话后回到新对话首页。
- 移除会把用户困在独立界面的 Workspace iframe；文件上传、任务 Context、成果保存和下一步操作保留在同一对话界面。
- 全局统一可点击按钮和链接的手型光标，禁用操作使用不可用光标。

### 验证
- 前端 ESLint：0 errors，保留既有 Settings Hook warning。
- Next.js 生产构建及 TypeScript 检查通过。

## [0.6.4] - 2026-08-31

### 视觉主题
- 默认主题由绿色切换为商务蓝，并把没有主题版本标记的历史默认绿色偏好迁移为蓝色；用户主动选择绿色后仍可保留该选项。
- 基础页面、交互态、按钮阴影和输入框边框改为使用主题变量，避免默认主题仍残留绿色交互色。

### 部署
- Docker 重新构建并发布前后端；后端 57 项测试、前端生产构建、端到端健康检查均通过。

## [0.6.3] - 2026-08-31

### Insight-Agent V1 工作空间
- 新增服务端 Agent Task Catalog 与 `POST /api/agent/routes`：业务对象、明确 AI Action、当前用户和服务端 Context Snapshot 统一路由为受隔离的 Agent Session。
- Session 新增任务标识、任务状态和默认目标；热点、Solution Intelligence、Requirement、Managed Solution 的入口改为“深入研究 / AI 分析 / 完善需求 / 架构设计”，不再跳转空白聊天页。
- 全局 Insight-Agent Shell 改为同一 Session 的 Floating、可调宽 Split 和 Full 三种视图；显示折叠的当前 Context、任务目标、下一步建议、最近工作，并在 Full 中复用既有 SSO 隔离 Workspace。
- Sidebar 增加本地记忆的一级折叠状态；Split 会为主业务区域让出可调宽度。

### Insight-Agent V2/V3 成果与知识
- Session Context 支持刷新、补充文本与按区块排除；每次模型调用仍只使用当前用户服务端保存的快照。
- 新增私有 `agent_artifacts`：从当前 Session 输出保存成果、关联来源业务对象 / Requirement / Solution，并在 Agent Home 显示最近成果。
- Artifact 只能由所有者提交团队知识审核；Admin 审核后才写入既有 Public Knowledge 目录，Admin 页面增加待审核列表。

### 验证
- 后端 pytest：57 passed；新增 Agent Action Routing 和 Artifact 所有权/输出提取测试。
- 前端 Next.js 生产构建通过，ESLint 无新增错误；保留既有 Settings Hook 警告。

## [0.6.2] - 2026-08-31

### Insight-Agent 子系统
- Insight-Agent 会话改为按用户持久化：支持新建、恢复、切换和删除最近会话；消息仅在流式回答完整结束后写入服务器端会话。
- 历史消息与 Context Snapshot 都由服务端按 `user_id` 读取，浏览器不再提交会话历史或系统提示词。

## [0.6.1] - 2026-08-31

### 文档与命名校准
- 将正式外部方案目录统一为阿里云/华为云多云目录；`/api/solutions/catalog` 为正式 API，`/api/solutions/aliyun` 仅保留兼容。
- 补齐 `aliyun_solutions`（历史表名）的 `vendor`、`content_snapshot`、`change_summary` 契约及 Prisma 镜像，修正 public 表计数、运维镜像版本、调度说明和 Agent 项目上下文。
- 将 Insight-Agent 专属规则保留在 `deploy/hermes/AGENTS.override.md`，移除根目录误放的规则与前端的无效引用；邮件和兼容 Chat 文案改为多云目录。

### Insight-Agent 原生对话
- 用站内原生流式对话页面替换 Hermes Dashboard iframe；点击洞察页“Agent 分析”会创建受权限保护的 Context Session，并自动发送首条分析请求。
- 新增登录态保护的 `POST /api/agent/chat/stream`；仅由服务端将当前用户的 Context Snapshot 注入模型提示词，客户端不能提交系统提示词或其他用户的 Session。

### 验证
- 静态核对 Compose、FastAPI 路由、运行时 schema、Prisma schema 与文档；未运行需要外部服务的部署或健康检查。

## [0.6.0] - 2026-08-29

### Context Bridge
- 新增统一 Context Service、对象绑定 Agent Session Snapshot、GitHub/Cloud Solution/Requirement/Solution 页面入口，以及隔离 Workspace 中的受限 Context 文件。
- 新增仅草稿的 Requirement/Solution Action 提案与用户确认 API；Agent 不持有业务数据库或写入凭据。
- 移除启动时无条件 `DROP TABLE ... CASCADE`，Schema 校准仅执行向后兼容的补齐。

### 验证
- 后端 pytest：47 passed（Python 3.9 测试环境）。前端 lint/build 与 Docker 验证待本次变更后运行。

## [0.5.0] - 2026-08-28

### 正式发布
- 将团队 AI Space 收敛为 InsightPro v0.5.0 的正式能力：统一账号、独立用户 Runtime / Workspace / Session、公共知识库、Admin 管理、基础审计与真实使用统计。
- 主系统和 Insight-Agent 保持独立部署与健康边界；Insight-Agent 故障不会影响 InsightPro 主系统可用性。
- 刷新项目 README、AI Space 运维/安全文档与数据库契约，明确产品边界和历史 `opencode_*` 兼容技术债。

## [0.4.0] - 2026-08-28

### 团队 AI Space 收尾
- InsightPro 保持唯一账号来源：普通用户与 Admin 的角色、禁用状态、SSO 和独立 AI 身份均按稳定 `user_id` 处理。
- 每位用户使用独立 Hermes Runtime、Linux UID、Workspace、Session 存储和端口；公共知识库独立挂载，成员只读、Admin 可维护。
- Admin 管理页补齐 Runtime/Workspace 状态、启停、Agent 禁用/恢复、公共知识管理，以及按真实 Runtime 请求汇总的今日/近 7 天基础使用统计。
- 新增 `agent_audit_events`，记录成员管理、Runtime 启停和公共知识库管理操作；不记录提示词、文件内容或密钥。

### 兼容性
- 产品层统一称为 Insight-Agent / AI Space。为避免影响已部署 SSO 表、回调和迁移，历史 `opencode_*` 数据表与少量兼容配置名暂时保留，后续单独评估迁移。

## [0.0.48] - 2026-08-26

### Insight-Agent 工作区命名
- SSO callback 自动读取当前 Supabase 用户姓名，缺失时使用邮箱前缀，并通过非敏感展示 Cookie 传给 Agent 启动脚本。
- 启动脚本自动更新 `/workspace` 的本地项目注册信息与 OpenCode 项目显示名；用户无需创建或命名 Workspace。
- InsightPro 登出时同时清理 Gateway Session Cookie 和工作区显示名 Cookie。

### 验证
- 真实 Supabase 用户完成 SSO；展示名 Cookie 编解码、`/workspace` 项目名称更新、30 天 Max-Age、会话创建/删除及登出 Cookie 清理全部通过。
- InsightPro full health 与 Insight-Agent 独立健康检查通过。

## [0.0.47] - 2026-08-26

### Insight-Agent 会话修复
- Gateway Session 从 5 分钟延长到 30 天，避免用户工作过程中 OpenCode API 被 302 重定向并显示“没有对话”。
- InsightPro 退出登录仍会立即撤销该用户的全部 Agent Gateway Session；一次性 SSO Ticket 仍保持 60 秒有效。

### 验证
- 真实 SSO Cookie 的 Max-Age 为 2592000 秒；通过 Gateway 创建并删除测试 Session 成功，登出后授权和展示 Cookie 均清理。

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
# v0.6.3 — 2026-09-02

- Agent 小窗支持切换历史会话、新建会话、当前页面上下文和首次分析提示。
- 空白小窗 / AI 工作区会话在关闭或离开时自动删除。
- 验证：`pytest -q backend/tests/test_agent_tasks.py backend/tests/test_solution_engineering_context.py`、`npm run lint`。
