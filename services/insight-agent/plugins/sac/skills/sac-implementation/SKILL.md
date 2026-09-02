---
name: sac-implementation
description: Build or maintain SAC Terraform and deployment assets. Use for resources, variables, outputs, providers, modules, user_data, bootstrap scripts, dependencies, or packaging.
---

# SAC Implementation Core

Produce minimal, deployable Terraform and bootstrap scripts that successfully launch the target application
on Huawei Cloud ECS. **一切以资源与应用的成功部署为目标。** This Skill creates local files; actual cloud deployment
requires proper provider credentials and `terraform apply`.

Use with `sac-project`. Load `sac-documentation` only when documents must change. New Practices and architecture
changes require a complete `sac-architecture` contract. For a small maintenance edit, the existing implementation
plus the explicit request is the contract.

## Required implementation input

Before editing, resolve: project, site, Region, optional variant, source file, requested behavior, and expected checks.

For new or architecture-changing work, also resolve:

```text
upstream revision and installation unit
image and compute flavor
disk type, size, and termination behavior
billing mode and period
VPC and subnet CIDRs
ingress ports and source CIDRs
EIP bandwidth and billing
runtime commands and persistent paths
external bootstrap source path, HTTPS object URL, and SHA-256 value
external service dependencies
outputs and access instructions
accepted deviations
```

Stop when a missing value would require inventing a resource, variable, default, endpoint, dependency, or
security choice.

## Terraform baseline and layout

For a new ECS-based Practice, start from the canonical baseline order:

```text
terraform/provider → variables → image data → VPC → subnet → security-group rules → EIP → ECS → outputs
```

Place the standard deployment directly in:

```text
practices/<project>/<site>/<region>/deploying-<project>_vN.tf
```

Use `practices/<project>/<site>/<region>/<variant>/` only when variants coexist in that Region. Never add a
redundant `terraform/` wrapper. Each deployable instance directory contains exactly one loadable `.tf` or
`.tf.json` file and optional `.extension`. It also contains exactly one `scripts/install_<project>.sh`, which is
published as the instance's external bootstrap object.

## Infrastructure rules

- Preserve the canonical image and `agent_list` unless the architecture contract records a reason to change them.
- Use `GPSSD` as the default EVS system disk type. Override only when the architecture contract explicitly requires it.
  Keep `delete_disks_on_termination` aligned with the durability decision.
- Current formal policy requires an EIP and `bandwidth_size`; preserve its billing mode and approved ingress scope.
- Keep administrative SSH restricted to the configured CloudShell `/32` source. Open only the approved application ports.
  Never expose database, cache, Docker API, debugger, or internal control ports.
- Use no random provider or random resource names.
- China vs international deployment differences:

  | Dimension | China (cn-*) | International |
  |---|---|---|
  | Docker image prefix | `docker.wangzhou3.top/` | Official Docker Hub or `ghcr.io` |
  | Docker daemon mirror | `"registry-mirrors": ["https://docker.wangzhou3.top"]` | None (direct pull) |
  | Docker CE source | Huawei Cloud apt mirror | Official Docker CE source |
  | apt/npm upstream | Default Huawei Cloud or mirror | Default official |

  China templates must use `docker.wangzhou3.top/` as image prefix for Docker Hub images in Compose files.
  Never use `docker.wangzhou3.top/` outside China templates.

- Mark secret inputs as `sensitive = true`. Keep generated runtime secrets on the instance with restrictive
  permissions. Never place secret values in URLs, outputs, logs, archives, or documentation.
- Reset the ECS root password in `user_data` with the simple inline pattern:
  ```bash
  echo 'root:${var.ecs_password}' | chpasswd
  ```
  Use an **unquoted** heredoc delimiter (`<<-EOT`, not `<<-'EOT'`) so Terraform interpolates variables.
  Do not add Base64 encode/decode wrappers or intermediate variables for the root password.

## user_data / 外联脚本分发规范

所有 Practice 统一使用外联分发：Terraform `user_data` 只负责重置密码、记录日志、下载、校验和
执行脚本；安装与应用部署逻辑全部放在同实例的 `scripts/install_<project>.sh` 中。不得内联 Compose、
安装步骤或辅助脚本。

### 对象路径

```text
# Source
practices/<project>/<site>/<region>[/<variant>]/scripts/install_<project>.sh

# Public Terraform object
https://<documentation-samples-host>/solution-as-code-publicbucket/solution-as-code-moudle/deploying-<project>/deploying-<project>.tf

# Public user_data script object
https://<documentation-samples-host>/solution-as-code-publicbucket/solution-as-code-moudle/deploying-<project>/userdata/install_<project>.sh
```

例如 Supabase 中国站模板：

```text
https://documentation-samples.obs.cn-north-4.myhuaweicloud.com/solution-as-code-publicbucket/solution-as-code-moudle/deploying-supabase/deploying-supabase.tf
https://documentation-samples.obs.cn-north-4.myhuaweicloud.com/solution-as-code-publicbucket/solution-as-code-moudle/deploying-supabase/userdata/install_supabase.sh
```

`documentation-samples` 完整主机名必须按目标 Region 使用已确认的公开分发端点，不得猜测数字后缀。
多部署形态在脚本名中加 `_<variant>` 后缀，例如 `install_<project>_ha.sh`。对象 URL 和
SHA-256 写在 Terraform `locals` 或 `user_data` 中，不得声明为客户可配置变量。不得写入 OBS 凭证或私有端点。

### 标准 launcher

```bash
#!/bin/bash
set -e
export DEBIAN_FRONTEND=noninteractive
LOGFILE="/var/log/${var.solution_name}-install.log"
exec 1>"$LOGFILE" 2>&1
echo 'root:${var.ecs_password}' | chpasswd

install -m 0700 /dev/null /tmp/install_<project>.sh
trap 'rm -f /tmp/install_<project>.sh' EXIT
curl -fL "${local.install_script_url}" -o /tmp/install_<project>.sh
echo "${local.install_script_sha256}  /tmp/install_<project>.sh" | sha256sum -c -
/tmp/install_<project>.sh
```

### 核心原则

1. **HTTPS + 完整性校验** — 下载必须使用 HTTPS 和 `curl -fL` 或等价失败感知选项，执行前必须用固定 SHA-256 校验
2. **源码与对象一致** — 外链脚本必须随 Practice 源码交付；发布后按字节计算并固定 SHA-256，不得执行仓库外不可审计的脚本
3. **敏感值不进参数与日志** — URL、命令行参数、输出和日志不得包含密码、Token 或云凭证；需向脚本传递的敏感值使用 root-only 临时文件或标准输入
4. **部署逻辑归脚本** — 包安装、Compose/配置生成、启动顺序、幂等处理和健康检查在 `install_*.sh` 内完成
5. **日志可追溯** — launcher 输出重定向 `/var/log/{solution_name}-install.log`；脚本不回显敏感值
6. **临时文件清理** — 用 `trap` 保证成功或失败时都删除下载脚本和临时敏感文件；不用 `curl | bash`

### 镜像与版本

- 使用架构合同批准的上游镜像或部署版本
- 不添加未批准的远端安装器或自建镜像

## Variables and outputs

Every customer-facing variable includes `default`, `description`, `type`, and `nullable`, in that order.
Add a `validation` block only when the implementation contract requires it. Password variables
(`ecs_password`, `db_password`, `*_password`) must **not** include a `validation` block — let the cloud API
enforce its own password policy.

### Validation condition rules

All `validation` blocks must follow these rules (see `skills/reference/validation-checklist.md` for full detail):

1. **Use `length(regexall(...)) > 0` style** — never `can(regex(...))`, inequality operators (`>=`, `<=`), `contains()`, or `length() >=`.
2. **No `tostring()` on number variables** — `regexall()` accepts `type = number` directly; wrapping with `tostring()` breaks RFS parameter-stage validation.
3. **No validation on password variables** — `*_password` variables omit the `validation` block entirely.
4. **Numeric ranges use regex segment matching** — e.g. 1–300 → `^([1-9][0-9]{0,1}|[1-2][0-9]{2}|300)$`.
5. **Enum values use alternation** — e.g. `^(postPaid|prePaid)$` instead of `contains([...])`.
6. **`error_message` language** — Chinese for `cn` templates, English for `intl` templates.

| Variable | Default | Type / nullable | Notes |
|---|---|---|---|
| `solution_name` | confirmed lowercase name | `string` / `false` | description states naming rule |
| `ecs_flavor` | confirmed flavor | `string` / `false` | validates expected format |
| `ecs_password` | `""` | `string` / `true`; `sensitive = true` | no validation block; never output |
| `system_disk_size` | confirmed GiB | `number` / `false` | validates range |
| `bandwidth_size` | confirmed Mbps | `number` / `false` | validates range |
| `charging_mode` | `"postPaid"` | `string` / `false` | `postPaid` or `prePaid` |
| `charging_unit` | `"month"` | `string` / `false` | `month` or `year` |
| `charging_period` | `1` | `number` / `false` | validates range |

Product-specific variables follow the same field rules and need an exact contract value.

**Outputs**: Provide one short primary `access_instructions` or `access_info` output. Add separate
`snake_case` outputs for each distinct value users must retrieve independently (`dashboard_url`,
`rest_api_url`, `ssh_command`, etc.). **Never join unrelated values with `|`, commas, or decorative
separators** — each distinct piece of information gets its own `output` block. Never output a password,
token, generated secret, or speculative detail.

## Local checks and fix loop

Run the smallest checks that cover the change:

- `terraform fmt -check` when Terraform is installed;
- HCL or JSON parsing;
- rendered `user_data` launcher and source bootstrap Bash syntax, SHA-256/URL consistency, and generated Compose validation;
- instance-scoped `rfs_policy` when applicable;
- affected documentation checks;
- the formal project quality entry before local delivery.

Return paths, commands, exit codes, findings fixed, and cloud checks not run. Tool or plugin download failure
is an environment result, not evidence that a template passed or failed in the cloud.

## Local delivery

When local packaging is requested and quality has passed:

1. Copy only authoritative Terraform, external bootstrap scripts, optional `.extension`, and required documents
   from `practices/` to the local delivery directory.
2. Byte-compare every copied file with its source.
3. Create the archive deterministically and list its contents.
4. Generate SHA-256 checksums for delivered files and the archive.
5. Update version records only with explicit authorization.

Return the release directory, site, Region, variant, archive, checksums, comparison result, and quality evidence.
