"""Lightweight repository scan for obvious secrets and local absolute paths."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
THIS_FILE = Path(__file__).resolve()

INCLUDE_SUFFIXES = {
    ".py",
    ".md",
    ".yaml",
    ".yml",
    ".toml",
    ".txt",
    ".env",
    ".example",
    ".ini",
}
EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "workspace",
}

PATTERNS = [
    ("openai_key_like", re.compile(r"\bsk-[A-Za-z0-9]{20,}\b")),
    ("windows_user_path", re.compile(r"\b[A-Za-z]:\\Users\\[^\s\"']+")),
    ("unix_home_path", re.compile(r"\b/home/[^\s\"']+")),
]


def should_scan(path: Path) -> bool:
    if path.resolve() == THIS_FILE:
        return False
    if any(part in EXCLUDED_DIRS for part in path.parts):
        return False
    if path.name == ".env":
        return False
    if path.suffix in INCLUDE_SUFFIXES:
        return True
    if path.name.endswith(".example"):
        return True
    return False


def main() -> int:
    findings: list[str] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or not should_scan(path):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for name, pattern in PATTERNS:
            for match in pattern.finditer(text):
                findings.append(f"{path.relative_to(ROOT)}:{name}:{match.group(0)}")

    if findings:
        print("Security scan findings:")
        for finding in findings:
            print(f" - {finding}")
        return 1
    print("Security scan passed (no obvious secrets or local absolute paths).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
