"""
跨方案一致性检查
===============
- 目录结构标准化（Terraform 直接位于实例目录，scripts/ 可选）
- .extension 文件检查
"""

import json
from pathlib import Path
from ..runner import CheckResult, PROJECT_CONFIG, ROOT


def load_quality_gate() -> dict:
    defaults = {
        "require_terraform_dir": False,
        "require_scripts_dir": False,
        "require_extension": False,
        "allow_inline_install_script": True,
    }
    if not PROJECT_CONFIG.exists():
        return defaults
    with PROJECT_CONFIG.open("r", encoding="utf-8") as f:
        config = json.load(f)
    return {**defaults, **config.get("quality_gate", {})}


def find_docs_dir(practice_path: Path, entry: dict) -> Path | None:
    practice_root = ROOT / "practices" / entry["name"]
    site = entry.get("site")
    locale = entry.get("locale")

    candidates = []
    if site == "intl" and locale:
        candidates.append(practice_root / "intl" / "docs" / locale)
    if site:
        candidates.append(practice_root / site / "docs")
    candidates.append(practice_root / "docs")
    candidates.append(practice_path.parent.parent / "docs")

    for docs_dir in candidates:
        if docs_dir.exists() and docs_dir.is_dir():
            return docs_dir
    return None


def run(practice_path: Path, entry: dict) -> list:
    results = []
    quality_gate = load_quality_gate()

    if entry.get("site") == "intl" and entry.get("locale"):
        results.append(CheckResult("consistency", True, "WARN",
                                   "历史 intl locale 实现层待迁移；新结构为 intl/<region>/<variant>"))

    # ── 1. 子目录检查 ──
    required_dirs = []
    optional_dirs = []
    if (practice_path / "terraform").exists():
        results.append(CheckResult("consistency", False, "ERROR", "不得使用冗余的 terraform/ 子目录"))
    if quality_gate["require_scripts_dir"]:
        required_dirs.append("scripts")
    else:
        optional_dirs.append("scripts")

    for sub in required_dirs:
        sub_path = practice_path / sub
        if not sub_path.exists():
            results.append(CheckResult("consistency", False, "ERROR", f"缺少 {sub}/ 子目录"))
        elif not sub_path.is_dir():
            results.append(CheckResult("consistency", False, "ERROR", f"{sub} 不是目录"))

    for sub in optional_dirs:
        sub_path = practice_path / sub
        if not sub_path.exists():
            results.append(CheckResult("consistency", True, "INFO", f"{sub}/ 子目录不存在（当前策略允许）"))
        elif not sub_path.is_dir():
            results.append(CheckResult("consistency", False, "ERROR", f"{sub} 不是目录"))

    # ── 2. .extension 文件 ──
    ext = practice_path / ".extension"
    if ext.exists():
        results.append(CheckResult("consistency", True, "INFO", ".extension 存在"))
    elif quality_gate["require_extension"]:
        results.append(CheckResult("consistency", False, "ERROR", "缺少 .extension"))
    else:
        results.append(CheckResult("consistency", True, "INFO", ".extension 不存在（可选）"))

    # ── 3. 文档目录 ──
    docs_dir = find_docs_dir(practice_path, entry)
    if docs_dir:
        md_files = list(docs_dir.glob("*.md"))
        results.append(CheckResult("consistency", True, "INFO", f"docs/ 目录: {len(md_files)} 个文档"))

    if not results:
        results.append(CheckResult("consistency", True, "INFO", "一致性检查通过"))
    return results
