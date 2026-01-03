#!/usr/bin/env python3
"""Set up VSCode for Python development with Ruff and Mypy.

Creates .vscode/settings.json and .vscode/extensions.json with
configurations that mirror the python-dev-framework plugin enforcement.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


VSCODE_SETTINGS: dict[str, Any] = {
    "[python]": {
        "editor.defaultFormatter": "charliermarsh.ruff",
        "editor.formatOnSave": True,
        "editor.codeActionsOnSave": {
            "source.fixAll.ruff": "explicit",
            "source.organizeImports.ruff": "explicit",
        },
    },
    "ruff.lineLength": 88,
    "ruff.lint.args": ["--select=E,W,F,I,B,C4,UP,ARG,SIM,T,TCH,PTH,ERA,PL,RUF,SLF"],
    "mypy-type-checker.args": ["--strict"],
    "python.analysis.typeCheckingMode": "strict",
}

VSCODE_EXTENSIONS: dict[str, list[str]] = {
    "recommendations": [
        "charliermarsh.ruff",
        "ms-python.mypy-type-checker",
        "ms-python.python",
    ]
}


def find_project_root() -> Path:
    """Find project root by looking for pyproject.toml."""
    cwd = Path.cwd()
    for parent in [cwd, *cwd.parents]:
        if (parent / "pyproject.toml").exists():
            return parent
    return cwd


def write_json_file(path: Path, data: dict[str, Any]) -> bool:
    """Write JSON file, returning True if file was created/updated."""
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.exists():
        existing = json.loads(path.read_text())
        if existing == data:
            return False

    path.write_text(json.dumps(data, indent=2) + "\n")
    return True


def main() -> int:
    """Create VSCode configuration files."""
    project_root = find_project_root()
    vscode_dir = project_root / ".vscode"

    settings_path = vscode_dir / "settings.json"
    extensions_path = vscode_dir / "extensions.json"

    settings_updated = write_json_file(settings_path, VSCODE_SETTINGS)
    extensions_updated = write_json_file(extensions_path, VSCODE_EXTENSIONS)

    if settings_updated or extensions_updated:
        print(f"VSCode configuration created in {vscode_dir}")
        print()
        print("Files created/updated:")
        if settings_updated:
            print(f"  - {settings_path.relative_to(project_root)}")
        if extensions_updated:
            print(f"  - {extensions_path.relative_to(project_root)}")
        print()
        print("Install recommended extensions:")
        print("  1. Open VSCode in this project")
        print("  2. Press Cmd+Shift+P -> 'Extensions: Show Recommended Extensions'")
        print("  3. Install all workspace recommendations")
    else:
        print("VSCode configuration already up to date.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
