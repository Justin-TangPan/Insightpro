"""
网络依赖扫描
===========
扫描外部网络依赖并分级:
  REACHABLE    — 华为云自有域名，内网可达
  NEED_MIRROR  — Docker Hub / GitHub / ghcr.io，需配置镜像
  HIGH_RISK    — curl | bash 高危模式
"""

import re
from pathlib import Path
from ..runner import CheckResult


# 已知安全的华为云域名（内网可达）
HUAWEI_DOMAINS = ["myhuaweicloud.com", "myhuaweicloud.cn", "huaweicloud.com"]

# 需要镜像加速的域名
MIRROR_DOMAINS = [
    "github.com", "githubusercontent.com",
    "docker.com", "docker.io", "ghcr.io", "quay.io",
    "gcr.io", "k8s.gcr.io", "registry.k8s.io",
    "pypi.org", "npmjs.org", "npmjs.com",
]

# 高危管道安装
HIGH_RISK_PATTERNS = [
    (r'curl\s+.*\|\s*(?:bash|sh)\b', "curl | bash 高危管道安装"),
    (r'wget\s+.*\|\s*(?:bash|sh)\b', "wget | sh 高危管道安装"),
]


def extract_urls(text: str):
    return re.findall(r'https?://[a-zA-Z0-9./_%?=&@:#-]+', text)


def classify(url: str):
    for d in HUAWEI_DOMAINS:
        if d in url:
            return "REACHABLE"
    for d in MIRROR_DOMAINS:
        if d in url:
            return "NEED_MIRROR"
    return "UNKNOWN"


def run(practice_path: Path, entry: dict) -> list:
    results = []
    deps = {}  # url -> [file refs]
    sources = []

    # 扫描 install 脚本
    scripts_dir = practice_path / "scripts"
    if scripts_dir.exists():
        for sh in sorted(scripts_dir.glob("**/*.sh")):
            content = sh.read_text(encoding="utf-8-sig", errors="replace")
            sources.append((sh.name, content))
            for url in extract_urls(content):
                deps.setdefault(url, []).append(sh.name)

    # 扫描 terraform 文件中的 URL
    tf_dir = practice_path
    if tf_dir.exists():
        for tf in tf_dir.glob("*.tf"):
            content = tf.read_text(encoding="utf-8-sig", errors="replace")
            sources.append((tf.name, content))
            for url in extract_urls(content):
                deps.setdefault(url, []).append(tf.name)

    need_mirror = 0
    high_risk = 0
    reachable = 0

    for filename, content in sources:
        for pattern, description in HIGH_RISK_PATTERNS:
            if re.search(pattern, content):
                high_risk += 1
                results.append(CheckResult("network", False, "ERROR", f"[高危] {description}", file=filename))

    for url, files in sorted(deps.items()):
        cls = classify(url)

        if cls == "REACHABLE":
            reachable += 1
        elif cls == "NEED_MIRROR":
            need_mirror += 1
            results.append(CheckResult("network", True, "WARN",
                                        f"[需镜像] {url[:100]}",
                                        detail=f"来源: {', '.join(files)}",
                                        file=files[0]))
        else:
            results.append(CheckResult("network", True, "INFO",
                                        f"[未知域名] {url[:100]}",
                                        detail=f"来源: {', '.join(files)}",
                                        file=files[0]))

    # 汇总
    summary = f"共 {len(deps)} 个外部依赖: {reachable} 可达, {need_mirror} 需镜像"
    if high_risk:
        summary += f", {high_risk} 高危!"

    results.insert(0, CheckResult("network", high_risk == 0,
                                   "ERROR" if high_risk > 0 else "INFO",
                                   summary))
    return results
