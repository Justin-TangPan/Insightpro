---
name: sac-quality
description: Review SAC Terraform and deployment assets. Use for validation, security audit, architecture/documentation consistency, diff impact, release readiness, or remediation verification.
---

# SAC Quality Core

Perform evidence-based review focused on **能否成功部署**。Reviews are read-only unless remediation is explicitly
requested. Static evidence never proves a real cloud deployment succeeded.

Use with `sac-project`. Read the frozen architecture contract or explicit maintenance request, exact diff,
current Terraform and documents, `project.config.json` (or `.sac/project.config.json` in an installed host),
and `skills/reference/validation-checklist.md` / `skills/reference/security-check-rules.md` as applicable.
Read the relevant layout or release contract only when that scope is under review.

## 审查核心：三问

以"能否成功部署"为审查标准，聚焦三个核心问题：

### 1. 语法正确性 — 代码能否被正确解析和执行？

- Terraform HCL 语法、格式化、provider 声明、变量和 validation 块是否合规？
- `user_data` launcher 和随源码交付的 `scripts/install_<project>.sh` 能否被 Bash 正确解析（`bash -n` 检查）？
- Docker Compose YAML 是否格式正确？
- 变量完整性：所有变量都声明了 `default`、`description`、`type`、`nullable`？
- 依赖引用：Terraform 资源间引用是否形成正确的依赖图？（无循环引用、无引用不存在的资源）
- `validation` 块是否只引用自己的变量（Terraform 拒绝跨变量条件）？
- `validation` condition 是否使用 `length(regexall(...)) > 0` 风格？禁止 `can(regex(...))`、不等式（`>=`/`<=`）、`contains()`、`length() >=`。
- 数字变量的 `regexall()` 是否直接接收 number 而非 `tostring()` 包裹？`tostring()` 会导致 RFS 参数填写阶段校验不触发。
- 密码变量（`*_password`）是否无 `validation` 块？
- `error_message` 语言是否正确：cn 用中文，intl 用英文？

### 2. 安全基线 — 是否存在可部署的安全风险？

- **凭证泄露**：是否有 AK/SK、API Key、Token、密码硬编码在模板或输出中？
- **密码变量**：`*_password` 是否标记 `sensitive = true`？是否被输出到 output、URL 或日志？
- **网络暴露**：数据库、缓存、Docker API、调试端口等内部服务是否被公网暴露？
- **管理入口**：SSH 是否限制为 CloudShell `/32` 源，而非 `0.0.0.0/0`？
- **容器风险**：是否有无依据的 `privileged`、Docker socket、host network 或危险挂载？
- **外链供应链**：脚本是否使用目标 Region 已确认的 `documentation-samples/.../deploying-<project>/userdata/install_*.sh` HTTPS 对象 URL，随 Practice 源码交付，并在执行前校验固定 SHA-256？是否避免 `curl | bash`？

### 3. 可部署性 — 模板在实际环境中能否成功部署？

- **变量完整性**：是否存在未提供默认值且非 `nullable` 的变量，会导致 apply 失败？
- **镜像可达性**：China 模板使用 `docker.wangzhou3.top/` 前缀？International 模板使用官方源？
- **启动顺序**：服务间依赖是否通过 Docker Compose `depends_on` 或简单脚本控制？
- **日志可追溯**：是否将 bootstrap 输出重定向到 `/var/log/{solution_name}-install.log`？
- **分发可用性**：源脚本路径、分发对象 key、URL 和 SHA-256 是否一致？目标 Region 是否能通过 EIP 访问该 HTTPS 端点？
- **幂等性**：包管理命令是否幂等？数据库初始化是否使用 `CREATE IF NOT EXISTS` 模式？
- **权限正确性**：bind-mount 的文件是否可被容器非 root 进程读取（`chmod 0644`）？避免全局 `umask 077` 破坏容器文件读取

### 附加检查（按需）

- **架构一致性**：资源、拓扑、网络、存储、计费、HA 是否与架构合同一致？
- **文档一致性**：参数表、端口、端点、安全声明、回滚说明是否与 Terraform 一致？
- **变更影响**：默认值变更是否会导致资源替换？兼容性影响？

## Static validation

Use existing repository entry points rather than reimplementing checks:

```bash
.venv-sac/bin/python -m scripts.tests.runner
```

In an npm-installed host:

```bash
PYTHONPATH=.sac/tooling .venv-sac/bin/python -m scripts.tests.runner
```

Run narrower instance checks when the task scope is small. Also run `terraform fmt -check`,
`terraform validate` in an initialized offline-capable environment, HCL/JSON parsing, rendered `user_data`
launcher and external bootstrap syntax (`bash -n`), bootstrap SHA-256, Compose validation, and instance-scoped
`rfs_policy` as applicable. If Terraform providers,
plugins, credentials, or network are unavailable, report the skipped command and cause.

Separate:
- automatically executed results with command and exit code;
- manual findings backed by file and line evidence;
- environment or tool limitations;
- real-cloud checks not run.

## Findings and classification

Classify findings by release impact:

- **blocker**: invalid or undeployable template, formal contract violation, critical/high security exposure,
  secret disclosure, architecture conflict, or unverifiable delivery.
- **non-blocking**: material warning, incomplete coverage, maintainability issue, or defense-in-depth
  opportunity that does not block the configured gate.
- **info**: evidence or improvement without release impact.

Security severity:
- **critical**: direct credential compromise, unauthenticated sensitive control, or equivalent immediate impact.
- **high**: practical remote compromise, broad privileged exposure, or release-blocking secret handling.
- **medium**: defense-in-depth gap with meaningful prerequisites.
- **low**: limited hardening opportunity.

A critical or high security finding is always a blocker unless an authorized, scope-specific accepted risk
already exists (with owner, scope, rationale, evidence, expiry, and compensating control). Do not create or
broaden accepted risk during review.

## Result contract

Set `passed=false` when any blocker remains. For each finding return:

```text
id and category
blocker/non-blocking/info
security severity when applicable
file and line when available
evidence without secret values
impact
required remediation
verification guidance
accepted-risk reference when applicable
```

Also return commands, exit codes, checks not run and why, architecture/document consistency result, cloud-test
boundary, and whether another Builder fix plus Reviewer pass is required.
