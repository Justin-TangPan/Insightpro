"""
Shell 脚本静态分析
=================
质量评分模型（满分 100），检测：
- set -euo pipefail / trap 错误保护
- 健康检查步骤
- 硬编码密码/Token
- mkdir -p 幂等性
- curl | bash 高危模式
- systemctl enable 开机自启
- timeout 超时保护
"""

import re
from pathlib import Path
from ..runner import CheckResult


# (points, msg) tuples
SCORE_CHECKS = {
    "set -euo pipefail":    (10, "建议使用 set -euo pipefail"),
    "set -e":               (5,  "缺少 set -e（出错时继续执行）"),
    "trap":                 (5,  "缺少 trap 错误处理"),
    "set -o pipefail":      (3,  "缺少 pipefail（管道错误被忽略）"),
    "health check":         (8,  "缺少健康检查/验证步骤"),
    "health":               (5,  "缺少 health 端点检测"),
    "systemctl enable":     (5,  "缺少 systemctl enable（重启后服务不启动）"),
    "systemctl start":      (3,  "缺少 systemctl start"),
    "mkdir -p":             (3,  "未使用 mkdir -p（非幂等）"),
    "timeout":              (5,  "缺少 timeout 超时保护"),
    "tee -a":               (3,  "缺少日志记录（tee）"),
    "log_":                 (2,  "缺少日志文件"),
    "STAGE":                (5,  "缺少阶段划分（STAGE 1/4）"),
    "date":                 (2,  "缺少时间戳输出"),
    "exit 0":               (3,  "缺少明确的退出码"),
}

RISK_PATTERNS = [
    (r'rm\s+-rf\s+/\s',                 -20, "危险: rm -rf / (根目录删除)"),
    (r'rm\s+-rf\s+/\*',                  -20, "危险: rm -rf /*"),
    (r'chmod\s+777\s+',                  -5,  "危险: chmod 777（权限过宽）"),
    (r'(PASSWORD|PASS|TOKEN|SECRET)\s*=\s*["\'][^"\']+["\']', -10, "脚本中硬编码密码/Token"),
    (r'(SK|AK|secret_key|access_key)\s*=\s*["\'][^"\']+["\']', -10, "脚本中硬编码云密钥"),
    (r'curl\s+.*\|\s*(?:bash|sh)\b',    -10, "高危: curl | bash（无验证管道安装）"),
    (r'wget\s+.*\|\s*(?:bash|sh)\b',    -10, "高危: wget | sh（无验证管道安装）"),
    (r'export\s+\w*PASSWORD\s*=',        -8,  "export 密码（环境变量泄露风险）"),
]


def run(practice_path: Path, entry: dict) -> list:
    results = []
    scripts_dir = practice_path / "scripts"

    if not scripts_dir.exists():
        return [CheckResult("scripts", True, "INFO", "scripts/ 目录不存在（跳过）")]

    sh_files = sorted(scripts_dir.glob("*.sh"))
    if not sh_files:
        return [CheckResult("scripts", True, "INFO", "scripts/ 中无 .sh 文件")]

    for sp in sh_files:
        content = sp.read_text(encoding="utf-8-sig", errors="replace")
        line_count = len(content.split("\n"))
        score = 60  # 基准分
        findings = []

        # 正向检查
        for pattern, (points, msg) in SCORE_CHECKS.items():
            if pattern in content:
                score += points
            elif points > 3:  # 仅报告重要缺失（points<=3 的不报）
                findings.append(("MISS", msg))

        # 负向检查（风险模式）
        for pattern, points, msg in RISK_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE):
                score += points
                findings.append(("RISK", msg))

        # 行数启发
        if line_count < 15:
            score -= 15
            findings.append(("MISS", f"仅 {line_count} 行，功能可能不完整"))
        elif line_count > 400:
            score -= 10
            findings.append(("WARN", f"{line_count} 行过长，建议拆分为模块"))

        # 文件大小
        size_kb = len(content) / 1024
        if size_kb > 50:
            findings.append(("WARN", f"{size_kb:.0f}KB 较大"))

        # 幂等性标记检查
        if "mkdir -p" in content:
            pass  # 好做法
        elif "mkdir " in content and "mkdir -p" not in content:
            findings.append(("WARN", "mkdir 未使用 -p（非幂等）"))

        score = min(100, max(0, score))

        rel_path = str(sp.relative_to(practice_path.parent.parent).as_posix())
        if score < 50:
            results.append(CheckResult("scripts", False, "ERROR",
                                        f"脚本质量 {score}/100: {sp.name}",
                                        detail="\n".join(f"[{s}] {m}" for s, m in findings),
                                        file=rel_path))
        elif score < 75:
            results.append(CheckResult("scripts", True, "WARN",
                                        f"脚本质量 {score}/100: {sp.name}",
                                        detail="\n".join(f"[{s}] {m}" for s, m in findings),
                                        file=rel_path))
        else:
            results.append(CheckResult("scripts", True, "INFO",
                                        f"脚本质量 {score}/100: {sp.name}"))

    return results
