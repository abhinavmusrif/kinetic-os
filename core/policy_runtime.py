"""Configuration and runtime policy bootstrapping."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def load_yaml(path: Path) -> dict[str, Any]:
    """Load YAML from file, returning empty mapping when missing."""
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Config file must contain a mapping: {path}")
    return data


def merge_dicts(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge dictionaries."""
    merged: dict[str, Any] = dict(base)
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = merge_dicts(merged[key], value)
        else:
            merged[key] = value
    return merged


def ensure_runtime_dirs(root: Path, config: dict[str, Any]) -> dict[str, Path]:
    """Ensure workspace and log directories exist and return resolved paths."""
    paths_cfg = config.get("paths", {})
    workspace_dir = (root / paths_cfg.get("workspace_dir", "workspace")).resolve()
    db_path = (root / paths_cfg.get("db_path", "workspace/ao.db")).resolve()
    audit_log_path = (root / paths_cfg.get("audit_log_path", "logs/audit.jsonl")).resolve()

    workspace_dir.mkdir(parents=True, exist_ok=True)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    audit_log_path.parent.mkdir(parents=True, exist_ok=True)

    return {
        "workspace_dir": workspace_dir,
        "db_path": db_path,
        "audit_log_path": audit_log_path,
    }


def load_effective_config(root: Path) -> dict[str, Any]:
    """Load and merge all runtime configuration files."""
    config_dir = root / "config"
    default_cfg = load_yaml(config_dir / "default.yaml")
    models_cfg = load_yaml(config_dir / "models.yaml")
    tools_cfg = load_yaml(config_dir / "tools.yaml")
    permissions_cfg = load_yaml(config_dir / "permissions.yaml")

    merged = merge_dicts(default_cfg, {"models": models_cfg, "tools_cfg": tools_cfg})
    merged["permissions"] = permissions_cfg
    return merged
