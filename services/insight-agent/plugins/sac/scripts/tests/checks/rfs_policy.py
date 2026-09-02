"""Enforce deployable-instance policies declared in project.config.json."""

import hashlib
import json
import re
from pathlib import Path

from ..runner import CheckResult, load_project_config


def _match(pattern: str, text: str) -> bool:
    return re.search(pattern, text, re.DOTALL) is not None


def _variable_blocks(text: str):
    for match in re.finditer(r'variable\s+"([^"]+)"\s*\{', text):
        depth = 1
        for index in range(match.end(), len(text)):
            depth += (text[index] == "{") - (text[index] == "}")
            if depth == 0:
                yield match.group(1), text[match.end():index]
                break


def run(practice_path: Path, entry: dict) -> list[CheckResult]:
    key = "/".join(filter(None, (
        entry.get("name"), entry.get("site"), entry.get("region"), entry.get("deploy_type")
    ))) or "/".join(practice_path.parts[-4:])
    policies = load_project_config().get("quality_gate", {}).get("practice_policies", {})
    policy = policies.get(key, {})

    tf_files = sorted((*practice_path.glob("*.tf"), *practice_path.glob("*.tf.json")))
    text = "\n".join(path.read_text(encoding="utf-8-sig", errors="replace") for path in tf_files)
    errors: list[str] = []

    if policy.get("single_active_template") and len(tf_files) != 1:
        errors.append(f"应只保留1个 active Terraform，实际为{len(tf_files)}个")

    if "user_data" not in text:
        errors.append("缺少 user_data launcher")
    else:
        if not all(marker in text for marker in ("https://", "sha256sum -c")):
            errors.append("user_data 必须通过 HTTPS 下载并在执行前校验 SHA-256")
        if not _match(
            r"https://documentation-samples(?:-\d+)?\.obs\.[a-z0-9-]+\.myhuaweicloud\.com/"
            r"solution-as-code-publicbucket/solution-as-code-moudle/deploying-[a-z0-9-]+/"
            r"userdata/install_[a-z0-9_-]+\.sh",
            text,
        ):
            errors.append("user_data 外链必须使用 documentation-samples/.../deploying-<project>/userdata/install_<project>.sh 格式")
        if not _match(r"(?:curl\s+-[^\n]*f[^\n]*L|wget\s+[^\n]*(?:--https-only|https://))", text):
            errors.append("user_data 必须使用失败感知的 HTTPS 下载")
        if _match(r"(?:curl|wget)[^\n]*\|\s*(?:bash|sh)\b", text):
            errors.append("禁止 curl/wget 直接管道到 shell")
        if _match(r'variable\s+"(?:install_script_url|bootstrap_url|obs_base_url)"', text):
            errors.append("外联脚本 URL 必须为固定实现值，不得暴露为客户变量")

    script_name = f"install_{entry.get('name', '')}.sh"
    scripts = sorted((practice_path / "scripts").glob("install_*.sh"))
    if len(scripts) != 1 or scripts[0].name != script_name:
        errors.append(f"scripts/ 必须仅包含 {script_name}")
    else:
        checksum = re.search(
            r'(?:install_script_sha256\s*=\s*"|echo\s+"?)([a-fA-F0-9]{64})(?:"|\s)', text
        )
        if not checksum:
            errors.append("user_data 必须固定 64 位脚本 SHA-256")
        elif hashlib.sha256(scripts[0].read_bytes()).hexdigest() != checksum.group(1).lower():
            errors.append("外联脚本 SHA-256 与源文件不一致")

    variables = set(re.findall(r'variable\s+"([^"]+)"', text))
    for name, body in _variable_blocks(text):
        foreign = sorted(set(re.findall(r'var\.([A-Za-z0-9_]+)', body)) - {name})
        if foreign:
            errors.append(f"variable {name} 的 validation 引用了其他变量: {', '.join(foreign)}")

    forbidden = sorted(variables.intersection(policy.get("forbidden_variables", [])))
    if forbidden:
        errors.append(f"禁止客户配置变量: {', '.join(forbidden)}")

    extension = practice_path / ".extension"
    if extension.exists():
        try:
            payload = json.loads(extension.read_text(encoding="utf-8"))
            for locale, values in payload.get("i18n", {}).items():
                exposed = set(values.get("variable", {}))
                if exposed != variables:
                    errors.append(
                        f".extension {locale} 参数与 Terraform 不一致: "
                        f"缺少 {sorted(variables - exposed)}，多余 {sorted(exposed - variables)}"
                    )
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f".extension 无法解析: {exc}")

    eip = policy.get("eip", {})
    bandwidth = eip.get("default_bandwidth")
    if bandwidth is not None and not _match(
        rf'variable\s+"bandwidth_size"\s*\{{.*?default\s*=\s*{bandwidth}\b', text
    ):
        errors.append(f"bandwidth_size 默认值必须为 {bandwidth}")
    charging_mode = eip.get("charging_mode")
    if charging_mode and not _match(
        rf'resource\s+"huaweicloud_vpc_eip".*?charging_mode\s*=\s*"{re.escape(charging_mode)}"', text
    ):
        errors.append(f"EIP charging_mode 必须固定为 {charging_mode}")
    bandwidth_charge_mode = eip.get("bandwidth_charge_mode")
    if bandwidth_charge_mode and not _match(
        rf'resource\s+"huaweicloud_vpc_eip".*?bandwidth\s*\{{.*?charge_mode\s*=\s*"{re.escape(bandwidth_charge_mode)}"', text
    ):
        errors.append(f"EIP bandwidth charge_mode 必须为 {bandwidth_charge_mode}")

    interface = policy.get("official_default_interface", {})
    port = interface.get("port")
    cidr = interface.get("remote_ip_prefix")
    if port is not None and not _match(
        rf'resource\s+"huaweicloud_networking_secgroup_rule".*?ports\s*=\s*{port}\b', text
    ):
        errors.append(f"安全组必须放行上游官方默认端口 TCP {port}")
    if interface.get("do_not_override_runtime_port") and "FRONTEND_PORT=" in text:
        errors.append("不得通过 FRONTEND_PORT 改写上游官方默认端口")
    if port is not None and "jiuwenswarm_url" in text and not _match(
        rf'output\s+"jiuwenswarm_url".*?:{port}\b', text
    ):
        errors.append(f"访问地址必须使用上游官方默认端口 {port}")
    if cidr and not _match(
        rf'resource\s+"huaweicloud_networking_secgroup_rule".*?remote_ip_prefix\s*=\s*"{re.escape(cidr)}"', text
    ):
        errors.append(f"公网接口 remote_ip_prefix 必须为 {cidr}")

    if errors:
        return [CheckResult("rfs_policy", False, "ERROR", message) for message in errors]
    return [CheckResult("rfs_policy", True, "INFO", "实例级 RFS 策略通过")]
