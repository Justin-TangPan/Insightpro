"""
Terraform 语法检查
================
每个部署实例只接受一个 active Terraform 文件。
检查内容：
- 变量 description 覆盖率 → WARN
- BOM 头检测 → ERROR
- EIP 带宽成本预警 → WARN
"""

import fnmatch
import re
import json
import subprocess
import textwrap
from pathlib import Path
from ..runner import CheckResult, load_project_config

try:
    import hcl2
except ImportError:  # pragma: no cover - formal repo environment provides python-hcl2
    hcl2 = None


USER_DATA = re.compile(
    r'user_data\s*=\s*<<-?(?P<tag>[A-Za-z0-9_]+)\s*\n(?P<body>.*?)^\s*(?P=tag)\s*$',
    re.MULTILINE | re.DOTALL,
)


def _shell_syntax(content: str) -> str | None:
    match = USER_DATA.search(content)
    if not match:
        return None
    script = textwrap.dedent(match.group("body"))
    script = re.sub(r'(?<!\$)\$\{[^}\n]+}', 'SAC_VALUE', script)
    script = script.replace('$${', '${').replace('%%{', '%{')
    return subprocess.run(["bash", "-n"], input=script, text=True, capture_output=True).stderr.strip() or None


def run(practice_path: Path, entry: dict) -> list:
    results = []
    tf_path = practice_path
    instance = "/".join(filter(None, (
        entry.get("name"), entry.get("site"), entry.get("region"), entry.get("deploy_type")
    )))
    exceptions = load_project_config().get("quality_gate", {}).get("architecture_exceptions", {})
    exception = next((value for pattern, value in exceptions.items()
                      if fnmatch.fnmatch(instance, pattern)), {})
    allowed_providers = set(exception.get("allowed_providers", ["huaweicloud"]))
    allowed_huaweicloud_keys = set(exception.get("allowed_huaweicloud_provider_keys", ["region"]))

    if (practice_path / "terraform").exists():
        results.append(CheckResult("tf_syntax", False, "ERROR", "不得使用冗余的 terraform/ 目录"))

    tf_files = sorted(tf_path.glob("*.tf"))
    json_files = sorted(tf_path.glob("*.tf.json"))
    active_files = tf_files + json_files
    if not active_files:
        results.append(CheckResult("tf_syntax", False, "ERROR", "实例目录中没有 Terraform 文件"))
        return results

    if len(active_files) != 1:
        names = ", ".join(path.name for path in active_files)
        results.append(CheckResult("tf_syntax", False, "ERROR",
                                   f"实例目录必须只有一个 active 模板，当前 {len(active_files)} 个: {names}"))
    else:
        results.append(CheckResult("tf_syntax", True, "INFO", "唯一 active Terraform 入口"))

    # ── 扫描所有 .tf 文件内容 ──
    for f in tf_files:
        content = f.read_text(encoding="utf-8-sig", errors="replace")

        if hcl2 is None:
            results.append(CheckResult("tf_syntax", False, "ERROR", "缺少 python-hcl2，无法执行 HCL 解析"))
        else:
            try:
                parsed = hcl2.loads(content)
                required = parsed.get("terraform", [{}])[0].get("required_providers", [{}])[0]
                providers = {key.strip('"') for key in required if not key.startswith("__")}
                if providers != allowed_providers:
                    results.append(CheckResult("tf_syntax", False, "ERROR",
                                               f"{f.name}: provider 应为 {sorted(allowed_providers)}，当前 {sorted(providers)}",
                                               file=str(f)))
                for block in parsed.get("provider", []):
                    for name, config in block.items():
                        if name.strip('"') == "huaweicloud":
                            keys = {key for key in config if not key.startswith("__")}
                            if keys != allowed_huaweicloud_keys:
                                results.append(CheckResult("tf_syntax", False, "ERROR",
                                                           f"{f.name}: huaweicloud provider 配置应为 {sorted(allowed_huaweicloud_keys)}，当前 {sorted(keys)}",
                                                           file=str(f)))
            except Exception as exc:
                results.append(CheckResult("tf_syntax", False, "ERROR", f"{f.name}: HCL 解析失败: {exc}", file=str(f)))

        shell_error = _shell_syntax(content)
        if shell_error:
            results.append(CheckResult("tf_syntax", False, "ERROR",
                                       f"{f.name}: user_data Bash 语法失败: {shell_error}", file=str(f)))

        # EIP 带宽预警
        for block in re.findall(r'resource\s+"huaweicloud_vpc_eip".*?\n}', content, re.DOTALL):
            bw = re.search(r'bandwidth\s*\{.*?size\s*=\s*(\d+)', block, re.DOTALL)
            if bw and int(bw.group(1)) > 100:
                results.append(CheckResult("tf_syntax", True, "WARN",
                    f"{f.name}: EIP 带宽 {bw.group(1)}Mbps 较大，请确认成本"))

        # 变量描述
        var_pattern = re.compile(r'variable\s+"(\w+)"')
        desc_pattern = re.compile(r'description\s*=')
        for match in var_pattern.finditer(content):
            var_name = match.group(1)
            opening = content.find('{', match.end())
            block = content[opening + 1:]
            depth, end = 1, 0
            for i, c in enumerate(block):
                if c == '{': depth += 1
                elif c == '}':
                    depth -= 1
                    if depth == 0: end = i; break
            var_block = block[:end]
            if not desc_pattern.search(var_block):
                results.append(CheckResult("tf_syntax", True, "WARN",
                    f"variable '{var_name}' 缺少 description"))

    for f in json_files:
        try:
            json.loads(f.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError as exc:
            results.append(CheckResult("tf_syntax", False, "ERROR", f"{f.name}: JSON 解析失败: {exc}", file=str(f)))

    # BOM 头检测
    for f in active_files:
        raw = f.read_bytes()
        if raw[:3] == b'\xef\xbb\xbf':
            results.append(CheckResult("tf_syntax", False, "ERROR", f"{f.name}: 包含 BOM 头（RFS 不允许）"))

    if not any(r.severity in ("ERROR", "WARN") for r in results):
        results.append(CheckResult("tf_syntax", True, "INFO", "Terraform 检查全部通过"))

    return results
