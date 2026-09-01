0.
# InsightPro Hermes Agent 接入提示词清单

## 第一轮：先审查，不写代码

```text
请完整阅读当前 InsightPro 项目。

当前下一阶段目标是在 InsightPro 中接入 Hermes Agent，作为平台唯一的交互式 AI Agent / AI 工作执行环境。

我的基本设想是：

InsightPro 继续负责技术解决方案洞察、Solution、Requirement 等业务能力；

Hermes Agent 保持使用自己的原生 Web UI，不在 InsightPro 中重新开发 Chat UI、Session、Agent Loop、Terminal、代码编辑等 Hermes Agent 已经具备的能力。

用户应该能够从 InsightPro 中点击一个“Hermes Agent / AI Agent”入口进入经过 InsightPro 项目定制后的原生 Hermes Agent。

本轮不要修改代码。

请重点审查：

1. 当前 InsightPro 前后端和 Docker / systemd 部署方式；
2. 当前导航和页面结构；
3. 当前认证方式；
4. 当前 AI Chat 的实现方式；
5. 当前项目目录和持久化目录；
6. Hermes Agent 最适合以什么方式作为独立服务加入当前架构；
7. Hermes Agent Web 最适合如何从 InsightPro 进入；
8. 是否适合使用反向代理、直接端口访问或其他方式；
9. Hermes Agent 数据和 Session 如何持久化；
10. 如何避免 Hermes Agent 与 InsightPro 主系统强耦合；
11. Hermes Agent 接入可能影响现有部署、端口、安全或运维的地方。

优先采用对现有 InsightPro 改动最小、稳定性最高的方式。

不要为了接入 Hermes Agent大规模重构 InsightPro。

全部使用中文。

最后给出一个简洁的实施方案，然后停止，不要开始编码。
```

---

# 第二轮：只把原生 Hermes Agent 跑起来

在确认第一轮方案没有明显问题以后：

```text
现在开始实施 Hermes Agent 接入的第一阶段。

本阶段目标非常简单：

让 Hermes Agent 作为 InsightPro 的独立服务稳定运行。

先不要做业务数据互通，也不要做 Context Bridge。

要求：

1. 基于当前 InsightPro 已有 Docker / systemd 体系集成 Hermes Agent；
2. Hermes Agent 必须作为独立运行服务；
3. 使用 Hermes Agent 原生 Web UI；
4. 不重新实现 Hermes Agent UI；
5. 不修改 Hermes Agent Core；
6. Hermes Agent 服务异常不得导致 InsightPro 前后端无法运行；
7. InsightPro 服务异常也尽量不要破坏 Hermes Agent 自身数据；
8. 为 Hermes Agent 设置独立持久化目录，避免容器重建导致 Session / 配置直接丢失；
9. Hermes Agent 的模型配置和凭据不得写死进代码或 Git；
10. 网络访问场景必须考虑 Hermes Agent Web 的访问保护；
11. 复用当前 InsightPro 的部署和健康检查思想，不新建另一套复杂运维系统。

Hermes Agent 当前默认 Web 端口可以使用 4096，如果当前环境存在冲突，请根据项目实际情况调整。

本阶段完成后的验收目标：

启动 InsightPro 时 Hermes Agent 可以一起启动；

浏览器可以打开 Hermes Agent 原生 Web；

Hermes Agent 可以正常创建 Session；

容器或服务重启后必要的数据仍然存在；

InsightPro 原有功能不受影响。

先根据当前代码说明准备修改哪些文件，然后直接实施。

完成后实际运行必要的构建、Docker 配置和健康验证。

不要开始做 Hermes Agent 与 Solution / Requirement 的数据互通。
```

---

# 第三轮：把入口放进 InsightPro

Hermes Agent 已经独立跑通后：

```text
现在继续 Hermes Agent 接入的第二阶段。

目标：

让用户可以自然地从 InsightPro 进入 Hermes Agent。

当前要求不是把 Hermes Agent UI 嵌套重写到 InsightPro，而是给原生 Hermes Agent 提供一个统一入口。

请根据当前项目实际架构选择最稳定的接入形式。

要求：

1. 在 InsightPro 主导航中增加“Hermes Agent”或“AI Agent”入口；
2. 点击后进入 Hermes Agent 原生 Web；
3. 不重新开发 Chat UI；
4. 不复制 Hermes Agent 前端代码；
5. 不通过 iframe 强行嵌入，除非你经过实际验证认为当前版本 Hermes Agent 使用 iframe 是最稳定的方案；
6. 如果采用反向代理或路径代理，需要实际验证资源加载、WebSocket、Session 和页面刷新；
7. 如果子路径代理存在兼容性风险，可以优先采用独立服务入口；
8. 用户应该能够方便地从 Hermes Agent 返回 InsightPro；
9. UI 风格上只需要保证入口属于 InsightPro 导航体系，不要求修改 Hermes Agent 原生界面。

本阶段不要实现 Solution → Hermes Agent 上下文传递。

重点只解决：

InsightPro
→ 点击 Hermes Agent
→ 原生 Hermes Agent 可正常使用

完成后进行浏览器级实际验证。
```

---

# 第四轮：把 Hermes Agent 变成“InsightPro 专用 Hermes Agent”

前面只是“装了一个 Hermes Agent”。

这一轮才开始定制。

```text
现在继续 Hermes Agent 接入的第三阶段。

当前 Hermes Agent 已经能够从 InsightPro 访问。

本阶段目标：

让 Hermes Agent 从一个普通 Coding Agent，变成理解 InsightPro 和技术解决方案业务背景的项目专用 Agent。

不要修改 Hermes Agent Core。

请优先使用 Hermes Agent 官方支持的项目级配置和 Instructions 机制完成定制。

需要完成：

1. 审查当前 InsightPro 是否已经存在适合作为 Hermes Agent 项目指令的 AGENTS.md；
2. 如果已有 AGENTS.md，基于现有内容增量完善，不覆盖有效规则；
3. 如果没有，则根据当前真实代码生成项目级 AGENTS.md；
4. 让 Hermes Agent明确理解 InsightPro 当前产品定位：
   “技术解决方案洞察平台”；
5. 告诉 Hermes Agent当前核心业务能力和产品边界；
6. 明确当前已经取消行业洞察、政策雷达、招标信息；
7. 让 Hermes Agent知道当前 Solution、Requirement 等 Workbench 能力；
8. 让 Hermes Agent知道外部 Solution Intelligence 与用户管理 Solution 的区别；
9. 让 Hermes Agent知道现有系统的主要技术架构、构建方式、测试方式和部署约束；
10. 告诉 Hermes Agent修改项目时优先增量开发，不随意大规模重构现有稳定系统。

请避免在 AGENTS.md 中堆入大量容易过期的数据。

长期稳定的：
- 架构原则
- 开发规范
- 产品边界
- 测试要求

写入 AGENTS.md。

容易变化的详细业务资料，可以放入独立文档，再使用 Hermes Agent 支持的 instructions 配置进行引用。

可以根据当前项目实际情况考虑：

PROJECT_SPEC.md
ARCHITECTURE.md
BUSINESS_CONTEXT.md

等文件。

完成后验证：

打开一个新的 Hermes Agent Session，

询问：
“这个项目是什么？”
“当前系统核心业务是什么？”
“修改这个项目应该注意什么？”

Hermes Agent 应能够基于项目文件正确回答，而不需要我重新解释项目背景。
```

---

# 第五轮：处理原来的 AI Chat

这一步不要一开始就删。

```text
现在审查 InsightPro 当前自带的 AI Chat 与新接入 Hermes Agent 的功能关系。

当前原则：

Hermes Agent 将成为 InsightPro 后续主要的交互式 AI Agent。

但是现有后台 AI 能力，例如：
- 技术摘要
- 技术价值评估
- Solution 摘要
- 自动分析
- 研报生成

不属于 Hermes Agent 的替代范围，应继续保留。

请重点区分：

后台 AI Pipeline

和

用户交互式 AI Agent

本轮请分析当前：
/api/chat
/api/chat/stream
全局 Chat UI
以及相关前端代码。

判断它们是否与 Hermes Agent 存在明显重复。

如果当前删除风险较低，可以将旧 Chat UI 标记为 Legacy 或减少入口；

如果删除可能影响现有功能，则暂时保留。

本轮不要为了“统一 AI”删除后台 AI Pipeline。

最终需要形成明确边界：

InsightPro 后台 AI
=
自动摘要、评分、分析、研报等系统能力

Hermes Agent
=
用户主动进行研究、Coding、方案分析和执行复杂任务的交互式 Agent

完成后说明建议，不要进行高风险删除。
```

---

# 第六轮：Hermes Agent 接入最终验收

```text
现在对 InsightPro + Hermes Agent 当前集成状态进行一次完整验收。

不要新增新功能。

请检查：

1. InsightPro 可以正常启动；
2. Hermes Agent 可以正常启动；
3. Docker / systemd 重启后两者能够恢复；
4. InsightPro 原有核心功能正常；
5. 主导航能够进入 Hermes Agent；
6. Hermes Agent 原生 Web 页面正常；
7. Hermes Agent 可以正常创建和继续 Session；
8. Hermes Agent 的持久化数据在重启后正常；
9. Hermes Agent 已加载 InsightPro 项目级 AGENTS.md / Instructions；
10. Hermes Agent 能够正确理解当前 InsightPro 项目；
11. Hermes Agent 修改代码时能够访问正确的项目目录；
12. Hermes Agent 不拥有不必要的宿主机文件访问范围；
13. Hermes Agent 的凭据没有进入 Git；
14. 网络访问的 Hermes Agent 服务存在必要保护；
15. InsightPro 与 Hermes Agent 日志不存在明显异常；
16. 前端 build、后端测试、Docker 配置和现有 Full Health 均通过。

如果发现问题，请直接修复可以安全修复的问题。

不要开始实现：

Solution → Hermes Agent Context Bridge
Requirement → Hermes Agent Context Bridge
Hermes Agent → InsightPro 数据写回

这些属于下一阶段。

完成后用中文给出：

当前架构
已完成能力
测试结果
访问方式
持久化方式
安全措施
已知问题
后续建议
```

---

# 当前阶段明确不要做的事情

在以上 Hermes Agent 基础接入全部完成之前，不要提前实现：

```text
Solution → Hermes Agent 自动上下文

Requirement → Hermes Agent 自动上下文

Insight → Hermes Agent 自动上下文

Hermes Agent 创建 Solution

Hermes Agent 创建 Requirement

Hermes Agent 写数据库

Hermes Agent 调 InsightPro API

Hermes Agent 自动执行 Scanner

复杂 Agent Workflow

多 Agent

自研 Chat UI
```

先把：

```text
InsightPro
↓
Hermes Agent入口
↓
原生 Hermes Agent
↓
理解 InsightPro 项目
↓
可以正常研究和 Coding
```

这一条链做稳定。

完成以后，再进入下一阶段：

```text
Insight / Solution / Requirement
↓
交给 Hermes Agent
```

即 Context Bridge。


1.
现在新增一个高优先级需求：

完善 InsightPro 用户系统，并让 Hermes Agent 完全复用 InsightPro 的用户身份，实现单点登录。

目标用户体验：

用户首先登录 InsightPro；
用户点击 InsightPro 中的 Hermes Agent / AI Agent；
如果当前 InsightPro Session 有效，应直接进入 Hermes Agent；
不允许再次要求用户输入 Hermes Agent Basic Auth 用户名或密码；
如果用户没有登录 InsightPro，则应先进入 InsightPro 登录流程；
登录成功后自动返回 Hermes Agent；
InsightPro 退出登录后，Hermes Agent 的访问授权也应失效或在合理短时间内失效。

当前原则：

InsightPro 是唯一用户身份来源，Hermes Agent 不再面向最终用户维护第二套账号体系。

当前 InsightPro 已使用 Supabase Auth，请优先复用现有用户、Session 和权限能力。

Hermes Agent 当前原生 Web 只支持服务级 Basic Auth，不原生支持 Supabase SSO，因此不要修改 Hermes Agent Core，也不要尝试把 Supabase 登录逻辑塞进 Hermes Agent 前端。

推荐从以下架构方向设计：

Browser
   │
   ├── InsightPro
   │      └── Supabase Auth
   │
   └── agent.xxx.com
            │
            ▼
     InsightPro Auth Gateway
            │
      验证用户身份
            │
            ▼
       Hermes Agent Web

Hermes Agent 仍然保持独立部署。

Auth Gateway 只负责：

判断当前用户是否已经登录 InsightPro；
建立 Hermes Agent 访问 Session；
未登录时跳转 InsightPro 登录；
登录完成后安全返回 Hermes Agent；
控制未授权用户不能直接访问 Hermes Agent。

不要依赖“InsightPro 隐藏菜单”作为安全措施。

不要把 Supabase Service Role、Hermes Agent 服务密码等敏感凭据下发到浏览器。

不要简单通过 URL query 参数长期传递 Supabase Access Token。

如果跨子域无法直接安全复用现有 Cookie，应设计短时、一次性的 SSO ticket / authorization code 流程，由服务端完成身份交换，并使用 HttpOnly、Secure、SameSite 合理配置的 Hermes Agent Gateway Session。

优先实现类似：

InsightPro 已登录
      ↓
点击 Hermes Agent
      ↓
InsightPro 服务端确认身份
      ↓
签发短时一次性 ticket
      ↓
agent.xxx.com/auth/callback
      ↓
Gateway 验证 ticket
      ↓
创建 HttpOnly Session
      ↓
Hermes Agent

ticket 必须：

有很短有效期；
只能使用一次；
与 InsightPro user_id 关联；
防止重放；
不包含数据库密码、Service Role 或模型 API Key；
验证失败直接拒绝访问。

同时完善 InsightPro 当前用户体系：

明确登录、注册、退出登录；
Session 过期处理；
当前用户信息获取；
未登录访问受保护功能时的行为；
用户状态在前端的统一处理；
Workbench 用户数据继续按照现有 user_id 隔离；
避免多个页面各自实现不同的登录判断。

非常重要：先审查 Hermes Agent 多用户隔离问题。

SSO 成功只代表“用户通过了身份验证”，不代表 Hermes Agent 本身已经实现多用户隔离。

当前 Hermes Agent 原生 Web 使用一个服务实例时，可能共享：

Session；
Workspace；
配置；
Provider 凭据；
文件系统。

因此实施前必须确认：

用户 A 登录以后，是否可能看到用户 B 的 Hermes Agent Session、文件或工作内容。

如果答案是可能：

不允许仅仅加一个 SSO Gateway 就把它定义成“完整多用户系统”。

请提出最小、安全的隔离方案。

首选考虑：

InsightPro User
      ↓
Auth Gateway
      ↓
用户独立 Hermes Agent Workspace / Instance

但本阶段不要未经评估就直接实现复杂的一用户一容器。

先明确：

当前 Hermes Agent Session 是否天然支持用户所有权；
单实例是否能够安全区分多个 InsightPro 用户；
如果不能，最合理的隔离层应该放在哪里；
单团队共享实例与正式多用户产品分别需要什么方案。

本阶段不要做：

Solution → Hermes Agent Context Bridge；
Requirement → Hermes Agent；
Insight → Hermes Agent；
Hermes Agent 写 InsightPro 数据；
修改 Hermes Agent Core；
自研 Hermes Agent UI；
把 Supabase Token直接暴露给 Hermes Agent；
仅靠共享 Basic Auth 密码冒充 SSO。

首先完成代码和架构审查，然后给出：

当前 InsightPro 用户系统还缺什么；
SSO 最小实现方案；
登录/退出完整时序；
Hermes Agent 多用户 Session 和 Workspace 是否安全隔离；
需要新增哪些组件；
是否需要数据库表；
对现有 Hermes Agent 独立部署方案有什么影响。

如果方案明确且不存在明显安全风险，可以直接实施用户系统完善 + SSO 基础能力。

如果发现单 Hermes Agent 实例无法保证不同 InsightPro 用户之间的数据隔离，则先实现认证基础设施，并明确报告隔离问题，不要为了完成需求而假装多用户隔离已经实现。

最终验收至少覆盖：

未登录 InsightPro
→ 点击 Hermes Agent
→ 登录 InsightPro
→ 自动进入 Hermes Agent

已登录 InsightPro
→ 点击 Hermes Agent
→ 直接进入

非法/过期 ticket
→ 无法进入

未授权直接访问 agent 域名
→ 无法进入

InsightPro 登出
→ Hermes Agent 授权失效

全程使用中文，优先复用现有 Supabase Auth，不大规模重构 InsightPro。


2.
请基于当前已经完成 Hermes Agent 独立部署和 InsightPro v0.4.0 的现状，继续推进下一阶段：

# Insight-Agent

产品层不再暴露 Hermes Agent 名称，统一更名为：

Insight-Agent

底层仍然复用 Hermes Agent 原生能力，不修改 Hermes Agent Core。

本阶段目标是把 Insight-Agent 正式变成 InsightPro 内置的 AI Agent 子系统，而不是一个外部跳转工具。

---

## 一、一级导航中的 Insight-Agent

InsightPro 一级 Sidebar 中保留独立入口：

Insight-Agent
AI 智能工作区

用户点击 Sidebar 的 Insight-Agent 后：

- 不跳转到外部页面；
- 不新开浏览器标签页；
- 在 InsightPro 当前框架内进入完整的 Insight-Agent 工作区；
- 左侧 InsightPro Sidebar 保留；
- 右侧主要内容区域用于完整显示 Insight-Agent / Hermes Agent 原生 Web UI；
- 尽量保留 Hermes Agent 原生 Session、Terminal、文件、Agent 等完整能力；
- 不重新开发 Hermes Agent 自己已经具备的 UI。

可以使用 iframe 或其他当前架构下更稳定的嵌入方式。

优先保证：
“部署独立，但产品体验集成”。

---

## 二、右下角 AI 助手由 Insight-Agent 完全替代

当前 InsightPro 右下角存在智能问答助手。

后续不再维护两套交互式 AI。

Insight-Agent 完全取代当前右下角 AI 助手。

需要区分：

### 用户交互式 AI

全部由 Insight-Agent 承担。

### InsightPro 后台 AI

继续保留，例如：

- 技术摘要；
- 技术价值评估；
- 解决方案分析；
- 自动分析任务；
- 研报生成；
- 采集后的 AI 数据加工。

这些属于后台 AI Pipeline，不属于 Insight-Agent 替代范围。

旧的浮动 Chat UI、Chat API、遗留 Agent 代码可以先分析依赖关系，再决定保留、标记 Legacy 或逐步清理。

不要因为接入 Insight-Agent 而误删业务型 AI 能力。

---

## 三、右下角 Insight-Agent 使用浮窗交互

普通浏览 InsightPro 时，右下角保留一个 Insight-Agent 浮动入口。

点击后：

打开一个真正的浮窗。

这个浮窗：

- 覆盖在 InsightPro 页面上；
- 不挤压主页面；
- 不改变页面布局；
- 默认出现在右下区域；
- 支持拖动；
- 支持调整大小；
- 支持最小化；
- 支持关闭；
- 支持最大化。

示意：

InsightPro 页面
                    ┌───────────────────┐
                    │ Insight-Agent     │
                    │                   │
                    │   Agent 浮窗      │
                    │                   │
                    │ [最小] [最大] [×] │
                    └───────────────────┘

点击“最大化”后：

进入和 Sidebar 点击 Insight-Agent 相同的完整工作区。

即：

右下角入口
    ↓
Insight-Agent 浮窗
    ↓
点击最大化
    ↓
完整 Insight-Agent Workspace

另外：

Sidebar → Insight-Agent
    ↓
直接进入完整 Workspace

两种入口必须尽量共用同一套 Agent Session。

不能出现：

浮窗一个 Session
+
完整 Workspace 又创建一个新 Session

的情况。

最大化以后：

- 当前对话不能丢；
- 当前 Session 不能重置；
- 当前 Agent 页面状态尽量保持；
- 隐藏右下角 Insight-Agent 浮动入口。

从完整 Workspace 点击“还原”：

恢复之前浮窗状态。

点击“关闭”：

回到原 InsightPro 页面，
右下角浮动入口重新出现。

---

## 四、Insight-Agent 可以理解整个 InsightPro，但本阶段只读

Insight-Agent 需要能够充分理解 InsightPro 项目。

它应该能够读取和分析：

- InsightPro 前端代码；
- InsightPro 后端代码；
- 数据模型；
- API；
- README；
- 架构文档；
- 产品说明；
- AGENTS.md；
- Solutions；
- Requirements；
- 技术热点；
- 解决方案洞察；
- 厂商动态；
- 搜索；
- AI Pipeline；
- 调度；
- 测试；
- Docker；
- systemd；
- 部署脚本；
- 非敏感运行配置。

目标：

用户进入 Insight-Agent 后，不需要重新解释“InsightPro 是什么”。

Insight-Agent 应天然理解：

- 产品定位；
- 当前模块；
- 系统架构；
- 数据关系；
- 产品边界；
- 当前开发规则。

但是：

本阶段 Insight-Agent 必须是 READ ONLY。

允许：

- 阅读；
- 搜索；
- 分析；
- 总结；
- 解释代码；
- 分析架构；
- 给修改建议；
- 生成方案；
- 生成代码草稿；
- 生成 Patch 建议。

禁止直接：

- 修改 InsightPro 源码；
- 修改数据库；
- 修改 Solution；
- 修改 Requirement；
- 修改生产配置；
- 执行部署；
- 删除文件；
- git push；
- git merge；
- 修改生产数据；
- 调用有副作用的 API。

不要只靠 Prompt 或 AGENTS.md 写一句“禁止修改”。

需要从实际权限层面尽量保证只读，例如：

- Workspace 挂载方式；
- 文件权限；
- Hermes Agent permission；
- Tool 权限；
- 容器权限；
- Shell 权限；
- API 权限。

重点审查：

即使 Agent 有 Terminal，
是否仍然可以绕过“只读规则”直接修改文件。

如果可以，需要真正限制。

同时：

Insight-Agent 不允许读取：

- 生产 .env；
- Supabase Service Role；
- 数据库密码；
- SMTP 密钥；
- 模型生产密钥；
- 其他 Secret。

“可以读取整个 InsightPro”指的是：

可以理解整个项目和非敏感信息，

不代表可以读取 Secret。

---

## 五、完善用户体系，并让 Insight-Agent 复用 InsightPro 用户系统

InsightPro 是唯一用户身份来源。

Insight-Agent 不再面向用户维护第二套登录体系。

目标体验：

用户登录 InsightPro
    ↓
点击 Insight-Agent
    ↓
直接进入
    ↓
不再输入 Hermes Agent 用户名和密码

如果用户未登录：

点击 Insight-Agent
    ↓
进入 InsightPro 登录
    ↓
登录成功
    ↓
返回 Insight-Agent

继续复用现有 Supabase Auth。

不要修改 Hermes Agent Core 来实现登录。

优先通过现有或新增的 Auth Gateway / SSO 层完成身份衔接。

需要重点验证：

- 已登录用户是否能直接进入；
- 未登录是否会被拦截；
- InsightPro 退出登录后 Insight-Agent 权限如何失效；
- 多用户情况下 Session 是否会串；
- 不同用户是否可能看到彼此 Hermes Agent Session；
- Workspace 是否存在用户间数据泄露。

特别注意：

“SSO 成功”不等于“多用户隔离已经完成”。

如果当前 Hermes Agent 单实例天然共享：

- Session；
- Workspace；
- 配置；
- 文件；

必须明确说明风险，并提出合理隔离方案。

不要假装已经实现多租户。

---

## 六、Insight-Agent 作为 InsightPro 的正式子项目维护

不要把 Insight-Agent 做成几段散落配置。

需要在 InsightPro 仓库中建立清晰的子项目或子模块目录。

目录结构由你根据当前仓库实际情况决定。

例如可以是：

insight-agent/

或：

services/insight-agent/

但不要机械照抄，如果现有仓库有更合适的组织方式，优先沿用。

这个子项目至少应包含完整文档。

### README.md

说明：

- Insight-Agent 是什么；
- 和 InsightPro 的关系；
- 为什么底层使用 Hermes Agent；
- 产品层为什么不再暴露 Hermes Agent 名称；
- 当前支持什么；
- 当前不支持什么；
- 如何启动；
- 如何停止；
- 如何访问；
- 如何调试；
- 如何升级；
- 如何排障。

### ARCHITECTURE.md

说明：

InsightPro
    ↓
Insight-Agent UI
    ↓
Auth / Gateway
    ↓
Hermes Agent
    ↓
Read-only InsightPro Workspace

并说明：

- 服务关系；
- 网络关系；
- 用户关系；
- Session 边界；
- Workspace；
- 数据边界；
- 安全边界；
- Hermes Agent 与 InsightPro 的解耦方式。

### SECURITY.md

说明：

- 为什么当前默认只读；
- Agent 能访问什么；
- 不能访问什么；
- Secret 如何隔离；
- 文件系统如何隔离；
- API 写权限如何限制；
- Terminal 风险如何控制；
- 多用户隔离现状；
- 未来如果开放写权限需要满足哪些条件。

### DEPLOYMENT.md

说明：

- Docker；
- Compose；
- systemd；
- 环境变量；
- 持久化；
- Session；
- Workspace；
- 健康检查；
- 反向代理；
- SSO；
- 升级；
- 回滚。

另外根据需要完善：

- AGENTS.md；
- BUSINESS_CONTEXT.md；
- PROJECT_CONTEXT.md；
- .env.example。

但不要生成大量重复文档。

原则：

稳定规则写在 AGENTS.md；

详细技术事实放架构文档；

实时变化内容从真实代码读取；

敏感内容永远不要写入文档。

---

## 七、产品边界

当前 InsightPro 的定位仍然是：

技术解决方案洞察平台。

Insight-Agent 是 InsightPro 的 AI 能力入口。

不得重新引入已经取消的：

- 行业洞察；
- 政策雷达；
- 招标信息。

当前 Solution 和 Requirement 功能保持现状。

本阶段暂时不做：

- Insight → Agent 自动上下文；
- Solution → Agent 自动上下文；
- Requirement → Agent 自动上下文；
- Agent 自动修改 Solution；
- Agent 自动修改 Requirement；
- Agent 写数据库；
- Agent 自动修改源码；
- Agent 自动提交 Git；
- Agent 自动部署；
- 多 Agent；
- Workflow 编排。

这些以后再做。

---

## 八、这一阶段的目标体验

用户正常打开 InsightPro：

首页 / 技术热点 / 解决方案洞察 / Solutions / Requirements

右下角存在：

Insight-Agent

用户可以：

方式一：

点击右下角
→ 打开 Insight-Agent 浮窗
→ 简单提问
→ 点击最大化
→ 进入完整 Agent Workspace

方式二：

点击 Sidebar 的 Insight-Agent
→ 直接进入完整 Agent Workspace

两种方式共用同一个 Agent。

完整 Workspace 打开时：

右下角 Insight-Agent 不显示。

退出 Workspace 后：

恢复原 InsightPro 页面和右下角 Agent 入口。

---

## 九、验收

至少实际验证以下场景。

### 场景 1

登录 InsightPro
→ 点击 Sidebar Insight-Agent
→ 直接进入完整 Workspace
→ 不再次登录
→ 右下角浮窗入口隐藏

### 场景 2

普通页面
→ 点击右下角 Insight-Agent
→ 浮窗打开
→ 与 Agent 进行对话
→ 最大化
→ 完整 Workspace
→ 原 Session 和上下文不丢失

### 场景 3

完整 Workspace
→ 点击还原
→ 回到浮窗
→ Session 继续存在

### 场景 4

完整 Workspace
→ 关闭
→ 返回之前 InsightPro 页面
→ 浮动入口恢复

### 场景 5

Insight-Agent 可以正确回答：

- InsightPro 是什么；
- 当前主要模块有哪些；
- 系统架构是什么；
- Solutions 和 Requirements 是什么；
- 当前 AI Pipeline 是什么；
- 当前部署方式是什么；
- 某个代码模块负责什么。

### 场景 6

要求 Agent：

“直接修改当前后端某个 Python 文件。”

实际权限应该阻止修改。

不能只看到 Agent 回复：

“根据规则我不能修改。”

而文件系统实际上仍然可写。

### 场景 7

Agent 无法访问：

- 生产 .env；
- Service Role；
- 数据库密码；
- SMTP 密钥；
- 生产模型密钥。

### 场景 8

未登录 InsightPro
→ 无法直接访问 Insight-Agent。

### 场景 9

用户 A 和用户 B
→ 检查 Session 和 Workspace 是否可能互相可见。

如果当前无法隔离，
必须明确记录为架构风险。

### 场景 10

Insight-Agent 服务停止：

InsightPro 其他功能仍正常。

InsightPro readiness 不应该因为 Insight-Agent 不可用直接失败。

---

## 十、实施方式

开始编码前：

先完整阅读当前 InsightPro v0.4.0 和已经实现的 Hermes Agent 接入代码。

不要根据旧文档或此前聊天内容假设系统现状。

先用中文简要输出：

1. 当前实现状态；
2. 准备如何改；
3. Insight-Agent 子项目如何组织；
4. 浮窗与完整 Workspace 如何复用 Session；
5. iframe / 嵌入方式是否可行；
6. SSO 如何实现；
7. 只读权限如何真正实现；
8. 多用户隔离当前有什么问题；
9. 预计修改哪些模块。

然后直接实施不存在明显风险的部分。

如果发现：

- iframe 安全限制；
- Hermes Agent 单实例无法多用户隔离；
- 只读权限无法可靠实现；
- SSO 存在明显安全问题；

不要使用不安全的临时绕过方式。

先完成可以安全落地的部分，并明确报告阻塞项。

最终完成后：

- 更新 README；
- 更新架构文档；
- 更新安全文档；
- 更新部署文档；
- 执行前端 Build；
- 执行后端测试；
- 执行 Docker / Agent 验证；
- 执行登录验证；
- 执行只读权限验证；
- 执行 Session 连续性验证；
- 执行原 InsightPro 功能回归。

最后用中文给出：

- 已完成内容；
- 架构变化；
- 修改文件；
- 测试结果；
- 当前限制；
- 安全风险；
- 后续建议。