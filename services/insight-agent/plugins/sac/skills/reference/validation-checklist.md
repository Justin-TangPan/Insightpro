# 模板验证清单（公共参考文档）

> `sac-quality` 使用本清单验证 SAC Practice；正式必需项以 `project.config.json` 和架构方案为准。

## 目录与模板

- 默认标准版位于 `practices/<practice>/<site>/<region>/`；仅同一 Region 有多个部署形态时使用 `<region>/<variant>/`；不建 `terraform/`，locale 仅用于 `intl/docs/<locale>/`。
- 每个 deployable instance 只有一个可加载 `.tf` 或 `.tf.json`，不得混用。
- 新 ECS 模板从基线顺序复制，保持 provider、变量、镜像、网络、EIP、ECS、outputs 的固定顺序。
- 每个变量都显式声明 `default`、`description`、`type`、`nullable`；`ecs_password` 还必须为 `sensitive = true`。密码变量（`*_password`）不设 `validation` 块，由 RFS/ECS 原生校验；其余变量使用 `length(regexall(...)) > 0` 风格的纯正则校验（详见下方"变量校验规则"章节）。
- `required_providers` 是对象且只声明实际需要的 Provider；Provider 配置只包含 `region`。
- 资源命名来自 `var.solution_name` 或稳定用户输入，不使用 UUID 或随机 Provider。
- 标准模板使用全内联 `user_data`，不依赖远端安装脚本。
- Terraform heredoc 中 Shell 命令替换使用 `$()`；只对需保留给下游配置的 `${...}` 使用 `$${...}`。

## 变量校验规则（Validation Condition）

所有 `validation` 块的 `condition` 必须遵守以下规范，确保 RFS 参数填写阶段即可触发校验并显示 `error_message`。

### 1. 统一使用 `length(regexall(...)) > 0` 风格

```hcl
# ✅ 正确
condition = length(regexall("^正则表达式$", var.xxx)) > 0

# ❌ 禁止
condition = can(regex("^正则表达式$", var.xxx))
condition = var.xxx >= 1 && var.xxx <= 300
condition = contains(["a", "b"], var.xxx)
condition = length(var.xxx) >= 8
```

### 2. 数字变量不加 `tostring()`

`regexall()` 直接接收 `type = number` 的变量。加 `tostring()` 会导致 RFS 参数填写阶段校验不触发，只有部署后才报错。

```hcl
# ✅ 正确
condition = length(regexall("^([1-9][0-9]{0,1}|[1-2][0-9]{2}|300)$", var.bandwidth_size)) > 0

# ❌ 禁止
condition = length(regexall("^...$", tostring(var.bandwidth_size))) > 0
```

### 3. 密码变量不做校验

`ecs_password`、`db_password`、`*_password` 等 sensitive 变量不设 `validation` 块，由云平台 API 原生校验密码策略。

### 4. 数字范围正则分段写法

| 范围 | 正则 | 说明 |
|---|---|---|
| 1–9 | `^[1-9]$` | 单数字 |
| 1–300 | `^([1-9][0-9]{0,1}\|[1-2][0-9]{2}\|300)$` | 1–9 + 10–99 + 100–299 + 300 |
| 40–1024 | `^([4-9][0-9]\|[1-9][0-9]{2}\|100[0-9]\|101[0-9]\|102[0-4])$` | 40–99 + 100–999 + 1000–1019 + 1020–1024 |

### 5. 枚举值正则写法

```hcl
# ✅ 正确
condition = length(regexall("^(postPaid|prePaid)$", var.charging_mode)) > 0
condition = length(regexall("^(month|year)$", var.charging_unit)) > 0

# ❌ 禁止
condition = contains(["postPaid", "prePaid"], var.charging_mode)
```

### 6. ECS 实例规格正则

覆盖华为云两种规格格式：

```hcl
condition = length(regexall("^([a-z][a-z0-9]{0,3}\\.)(x|[1-9][0-9]{0,1}x)large\\.[1-9][0-9]{0,1}$|^x1\\.([1-9]|1[0-6])u\\.[1-9][0-9]{0,1}g$", var.ecs_flavor)) > 0
```

- 分支1：`c7n.2xlarge.2` 型 — 前缀 + Nx/x + large + 后缀
- 分支2：`x1.8u.16g` 型 — x1 + Nu + Ng

### 7. error_message 语言

- **中国站（cn）**：`error_message` 使用中文
- **国际站（intl）**：`error_message` 使用英文

## 部署逻辑

- 包管理命令非交互、可重复执行，并使用与站点匹配且已验证的软件源。
- `system_disk_type` 为 `GPSSD`；`system_disk_size` 的 `description` 不包含磁盘类型。
- 日志重定向到 `/var/log/{solution_name}-install.log`（`LOGFILE` 变量 + `exec` 重定向）。
- `user_data` 中不使用 `bun install -g`；当 npm 已安装时使用 `npm install -g`。
- `cn` 模板使用 `docker.wangzhou3.top/` 作为 Docker Hub 镜像前缀；`intl` 使用 `docker.io` 或 `ghcr.io`。
- 配置和有状态目录持久化；数据库初始化幂等，权限和 schema 完整。
- `user_data` 是单段内联 Bash，并保留 Hermes 基线形状；仅为上游已验证的运行方式修改运行时命令，任何偏离必须记录在 architecture contract。
- 有一个简短的 `access_instructions` 或 `access_info` 主输出；用户必须单独获取的 API 地址、SSH 命令、凭证查看命令、日志路径等使用独立、有意义的 `snake_case` outputs，不用 `|` 或其他装饰分隔符拼接。
- 所有 outputs 都不得包含密码、Token、生成的 Secret 或其他敏感值，也不为非必要信息增加输出。
- 变量、上游地址、端口、输出和清理行为与架构方案一致。

## 安全

- 不含 AK/SK、API Key、Token、私有端点或固定生产密码。
- 敏感变量必须声明 `sensitive = true`，不得进入 URL、output 或日志；既有模板因兼容性在 `user_data` 中传递密码时记录风险并限制作用域，不再作为项目级硬阻断。
- 公网入口和管理端口严格匹配架构方案；数据库等内部端口不做宽泛公网暴露。
- 容器不使用无依据的 `privileged`、Docker socket、host network 或危险宿主机挂载。
- 密码经安全输入或部署时生成，不因模板渲染、命令行或日志而泄露。

## 文档与国际化

- 文档名称、语言和目录符合 Practice Layout Contract；Hermes 指南必须覆盖官方 `hermes_01` 至 `hermes_08` 的概述、成本、准备、部署、开始使用、卸载和附录，方案详情必须覆盖官方方案页面的 Hero、优势、架构部署、应用场景、拓展和服务亮点。
- `cn` 提供中文文档；`intl` 同时提供 `zh-cn` 与 `en-us` 文档，并保持技术事实一致。
- `.extension` 与 Terraform 变量一致；国际站 `.extension` 同时提供中英文文案。
- Terraform output 的 `description` 使用简短纯 ASCII 文本；output 值避免 `|` 等装饰性分隔符和不必要的特殊字符。
- 文档中的参数、端口、输出、健康检查和故障排查均可从实现追溯，不含 TODO 或未解释占位符。

## 结果判定

- 静态检查不得冒充云上部署成功。
- 工具或环境失败与产品失败分开报告。
- 存在正式合同错误、安全门禁错误或不可部署项时 `passed=false`。
