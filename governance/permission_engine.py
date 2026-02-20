"""Permission policy enforcement."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from governance.action_sandbox import is_within_workspace
from governance.budget_guard import BudgetGuard


@dataclass
class PermissionDecision:
    """Represents allow/block decision."""

    allowed: bool
    reason: str


class PermissionEngine:
    """Policy engine for tool/action allow/deny checks."""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        cfg = config or {}
        self.allow_shell = bool(cfg.get("allow_shell", False))
        self.allow_file_write_outside_workspace = bool(
            cfg.get("allow_file_write_outside_workspace", False)
        )
        self.allow_os_automation = bool(cfg.get("allow_os_automation", False))
        self.allow_network = bool(cfg.get("allow_network", False))
        self.require_confirmation_for = set(cfg.get("require_confirmation_for", []))
        self.budget_guard = BudgetGuard(float(cfg.get("max_daily_budget_usd", 0)))

    @classmethod
    def from_yaml(cls, path: Path) -> PermissionEngine:
        """Build engine from YAML file path."""
        with path.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        if not isinstance(data, dict):
            raise ValueError("permissions.yaml must be a mapping.")
        return cls(config=data)

    def check(
        self,
        *,
        action: str,
        tool_name: str,
        metadata: dict[str, Any] | None = None,
        workspace_dir: Path | None = None,
    ) -> PermissionDecision:
        """Evaluate policy for a requested action."""
        metadata = metadata or {}
        action_l = action.lower()
        tool_l = tool_name.lower()

        if "shell" in tool_l and not self.allow_shell:
            return PermissionDecision(False, "Shell execution disabled by policy.")
        if "os_automation" in action_l and not self.allow_os_automation:
            return PermissionDecision(False, "OS automation disabled by policy.")
        if metadata.get("requires_network") and not self.allow_network:
            return PermissionDecision(False, "Network operations disabled by policy.")
        if metadata.get("requires_confirmation"):
            return PermissionDecision(False, "Action requires explicit confirmation.")

        sensitive_hits = [word for word in self.require_confirmation_for if word in action_l]
        if sensitive_hits:
            return PermissionDecision(
                False,
                f"Action requires confirmation: {', '.join(sorted(sensitive_hits))}.",
            )

        target_path = metadata.get("target_path")
        if target_path and workspace_dir is not None:
            path_obj = Path(str(target_path))
            if not self.allow_file_write_outside_workspace and not is_within_workspace(
                path_obj, workspace_dir
            ):
                return PermissionDecision(False, "Write outside workspace is blocked.")

        estimated_cost = float(metadata.get("estimated_cost_usd", 0.0))
        if estimated_cost > 0 and not self.budget_guard.can_spend(estimated_cost):
            return PermissionDecision(False, "Budget limit exceeded.")

        return PermissionDecision(True, "Allowed by policy.")

    def charge(self, amount_usd: float) -> bool:
        """Charge budget if possible."""
        return self.budget_guard.charge(amount_usd)
