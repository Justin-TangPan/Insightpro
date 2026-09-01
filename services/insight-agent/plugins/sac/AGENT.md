# 华为云解决方案实践插件

此插件服务于华为云 Solution Practice；它不替代 InsightPro 的 Requirement、Solution、Artifact 和人工确认边界。

## 何时启用

当任务涉及华为云方案设计、Terraform、部署脚本、部署验证、PoC 或交付材料时启用。普通技术调研、非云方案讨论和不改变实践的文案修改不强制进入本流程。

## 核心技能

- `sac-project`：以当前业务对象、已批准架构合同、实现文件和验证记录为事实源；区分事实、推断、假设、未知与用户决策。
- `sac-architecture`：先确认场景、组件、网络、存储、可用性、依赖、成本、风险与验收边界，再形成架构合同。
- `sac-implementation`：按已确认合同生成最小 Terraform、bootstrap 与部署资产；Secret 不写入源码、输出、日志或成果。
- `sac-quality`：独立检查 Terraform、网络暴露、敏感输出、外部依赖和文档一致性；静态检查不等于真实云验证。
- `sac-documentation`：基于已验证事实生成部署指南、方案详情、参数、回滚与交付清单。

## 工作流与门禁

```text
Discover / Understand → Architecture Contract（人工确认）
→ Implementation → Review → Verification
→ 可选 Cloud Validation（再次明确确认）
→ Documentation → Artifact 审核 → Delivered / Knowledge
```

- 新实践或拓扑、网络、数据、可用性、外部依赖变更：必须先完成 Architecture Contract。
- 小型、无架构影响的实现修改：Implementation → Review 即可。
- 仅评审：只输出 findings，不修改实现。
- 只有真实资源、应用健康和核心流程的对应证据，才能称为已部署或已验证。
- 创建真实云资源、发布、提交或写入业务对象，仍需 InsightPro 的明确确认。

## 架构合同最小内容

记录：目标与范围、证据与假设、区域和部署形态、组件与云资源映射、端口/CIDR/TLS、持久化与备份、依赖和启动顺序、变量与输出、成本风险、验证和回滚、待确认项。

## 交付与证据

每阶段成果包含：当前阶段、输入、完成项、文件或 Artifact、检查命令与结果、未解决风险、所需决策和下一步。证据中脱敏凭据、Token、密码、私有端点与绝对本机路径。
