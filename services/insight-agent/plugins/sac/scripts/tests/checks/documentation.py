"""Documentation checks used by the formal SAC quality gate.

The checker deliberately supports both historical documentation layouts and the
current site-level contract.  Strict checks are opt-in so an incremental rollout
does not invalidate practices that have not entered the document pipeline yet.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from ..runner import CheckResult, ROOT, load_project_config


REQUIRED_DEPLOY_ZH = ("部署", "验证", "卸载")
REQUIRED_DEPLOY_EN = ("deploy", "verif", "uninstall")
PLACEHOLDER_RE = re.compile(r"\bTODO\b|待补充|待技术确认|缺少来源|\{\{[^}]+\}\}", re.I)


def _document_dirs(practice_root: Path) -> list[Path]:
    """Return compatible site-level document directories without duplicates."""
    candidates = [
        practice_root / "cn" / "docs",
        practice_root / "intl" / "docs" / "zh-cn",
        practice_root / "intl" / "docs" / "en-us",
        practice_root / "intl" / "zh-cn" / "docs",  # historical layout
        practice_root / "intl" / "en-us" / "docs",  # historical layout
    ]
    return [path for path in candidates if path.is_dir()]


def _is_deployment(path: Path) -> bool:
    return "部署" in path.name or "deployment" in path.name.lower()


def _is_details(path: Path) -> bool:
    lower = path.name.lower()
    return "方案详情" in path.name or "solution-details" in lower or "solution details" in lower


def _markdown_checks(path: Path, strict: bool) -> list[CheckResult]:
    text = path.read_text(encoding="utf-8", errors="replace")
    results: list[CheckResult] = []
    fences = len(re.findall(r"^```", text, flags=re.M))
    if fences % 2:
        results.append(CheckResult("docs", False, "ERROR", f"{path.name} 存在未闭合代码块", file=str(path)))
    if PLACEHOLDER_RE.search(text):
        severity = "ERROR" if strict else "WARN"
        results.append(CheckResult("docs", not strict, severity, f"{path.name} 含待确认或异常占位符", file=str(path)))
    headings = [line for line in text.splitlines() if re.match(r"^#{1,6}\s+\S", line)]
    if not headings:
        severity = "ERROR" if strict else "WARN"
        results.append(CheckResult("docs", not strict, severity, f"{path.name} 缺少 Markdown 标题", file=str(path)))
    if _is_deployment(path):
        lowered = text.lower()
        required = REQUIRED_DEPLOY_ZH if re.search(r"[\u4e00-\u9fff]", text) else REQUIRED_DEPLOY_EN
        missing = [item for item in required if item.lower() not in lowered]
        if missing:
            severity = "ERROR" if strict else "WARN"
            results.append(CheckResult("docs", not strict, severity,
                                       f"{path.name} 缺少部署文档关键章节: {', '.join(missing)}", file=str(path)))
    size_kib = path.stat().st_size / 1024
    if size_kib > 500:
        results.append(CheckResult("docs", True, "WARN", f"{path.name} 为 {size_kib:.0f}KB，建议拆分", file=str(path)))
    return results


def _pipeline_report_checks(practice_root: Path) -> list[CheckResult]:
    report = ROOT / "output" / "document-pipeline" / practice_root.name / "quality-report.json"
    if not report.exists():
        return []
    try:
        payload = json.loads(report.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [CheckResult("docs", False, "ERROR", f"文档质量报告不可读取: {exc}", file=str(report))]
    errors = payload.get("errors", [])
    status = payload.get("status", "warning")
    if status == "fail" or errors:
        return [CheckResult("docs", False, "ERROR", f"文档流水线报告含 {len(errors)} 个阻断问题", file=str(report))]
    return [CheckResult("docs", True, "INFO", f"文档流水线报告状态: {status}", file=str(report))]


def run(practice_path: Path, entry: dict) -> list[CheckResult]:
    practice_root = ROOT / "practices" / entry["name"]
    config = load_project_config().get("quality_gate", {}).get("documentation", {})
    strict = bool(config.get("strict", False))
    require_docx = bool(config.get("require_docx", False))
    docs_dirs = _document_dirs(practice_root)
    results: list[CheckResult] = _pipeline_report_checks(practice_root)

    if not docs_dirs:
        severity = "ERROR" if strict else "WARN"
        results.append(CheckResult("docs", not strict, severity, "未发现兼容的站点级 docs 目录"))
        return results

    md_files = sorted({path for directory in docs_dirs for path in directory.glob("*.md")})
    docx_files = sorted({path for directory in docs_dirs for path in directory.glob("*.docx")})
    if not md_files:
        severity = "ERROR" if strict else "WARN"
        results.append(CheckResult("docs", not strict, severity, "docs 目录中无 Markdown 文档"))
        return results

    maximum = int(config.get("maximum_markdown_files_per_solution", 6))
    if len(md_files) > maximum:
        results.append(CheckResult("docs", False, "ERROR",
                                   f"正式 Markdown 文档 {len(md_files)} 份，超过上限 {maximum}"))

    has_deploy = any(_is_deployment(path) for path in md_files)
    has_details = any(_is_details(path) for path in md_files)
    for present, label in ((has_deploy, "部署指南"), (has_details, "Solution Details/方案详情")):
        severity = "INFO" if present else ("ERROR" if strict else "WARN")
        results.append(CheckResult("docs", present or not strict, severity,
                                   f"包含{label}" if present else f"缺少{label}"))

    for path in md_files:
        results.extend(_markdown_checks(path, strict))

    if require_docx and not docx_files:
        results.append(CheckResult("docs", False, "ERROR", "严格门禁要求 Word 文档，但未发现 .docx"))
    elif docx_files:
        for path in docx_files:
            if path.stat().st_size < 1024:
                results.append(CheckResult("docs", False, "ERROR", f"{path.name} 不是有效大小的 Word 文档", file=str(path)))
        results.append(CheckResult("docs", True, "INFO", f"发现 {len(docx_files)} 个 Word 文档"))
    return results
