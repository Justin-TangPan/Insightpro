#!/usr/bin/env python3
"""Fail deployment when product version labels drift apart."""

import json
import re
from pathlib import Path


root = Path(__file__).resolve().parent.parent
version = json.loads((root / "frontend/package.json").read_text())["version"]
assert re.fullmatch(r"1\.0\.0-rc\.[1-9]\d*", version), version

lock = json.loads((root / "frontend/package-lock.json").read_text())
assert lock["version"] == lock["packages"][""]["version"] == version

checks = {
    "backend/settings.py": [f'os.getenv("APP_VERSION", "{version}")'],
    "compose.yaml": [
        f"image: insight-web-backend:{version}",
        f"image: insight-web-frontend:{version}",
        f'APP_VERSION: "{version}"',
    ],
    "README.md": [f"`v{version}`", f"version-{version.replace('-', '--')}"],
    "log/versions.md": [f"当前候选版本：`{version}`", f"## [{version}]"],
}
for filename, expected in checks.items():
    content = (root / filename).read_text()
    for value in expected:
        assert value in content, f"{filename}: missing {value}"

print(f"Product version consistent: v{version}")
