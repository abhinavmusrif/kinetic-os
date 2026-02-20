"""Safe execution gate wrapping governance checks and auditing."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from executor.rollback_manager import RollbackManager
from governance.audit_logger import AuditLogger
from governance.permission_engine import PermissionEngine
from governance.risk_scoring import score_action_risk


class SafeRunner:
    """Runs actions only when policy and risk allow."""

    def __init__(
        self,
        permission_engine: PermissionEngine,
        audit_logger: AuditLogger,
        workspace_dir: Path,
        max_allowed_risk: float = 0.85,
    ) -> None:
        self.permission_engine = permission_engine
        self.audit_logger = audit_logger
        self.workspace_dir = workspace_dir
        self.max_allowed_risk = max_allowed_risk
        self.rollback_manager = RollbackManager(workspace_dir)

    def run(
        self,
        *,
        action: str,
        tool_name: str,
        inputs: dict[str, Any],
        metadata: dict[str, Any] | None,
        execute: Callable[[], Any],
    ) -> dict[str, Any]:
        """Evaluate policy+risk and execute action callable if allowed."""
        metadata = metadata or {}
        decision = self.permission_engine.check(
            action=action,
            tool_name=tool_name,
            metadata=metadata,
            workspace_dir=self.workspace_dir,
        )
        risk = score_action_risk(action=action, tool_name=tool_name, payload=inputs)
        if not decision.allowed:
            reason = decision.reason
            self.audit_logger.log(
                action=action,
                tool=tool_name,
                inputs=inputs,
                outcome="blocked",
                allowed=False,
                reason=reason,
            )
            return {
                "success": False,
                "action": action,
                "tool": tool_name,
                "outcome": f"Blocked: {reason}",
                "risk_score": risk,
                "confidence": 1.0,
                "evidence_refs": [],
            }
        if risk > self.max_allowed_risk:
            reason = f"Risk score {risk:.2f} exceeds threshold {self.max_allowed_risk:.2f}."
            self.audit_logger.log(
                action=action,
                tool=tool_name,
                inputs=inputs,
                outcome="blocked",
                allowed=False,
                reason=reason,
            )
            return {
                "success": False,
                "action": action,
                "tool": tool_name,
                "outcome": f"Blocked: {reason}",
                "risk_score": risk,
                "confidence": 1.0,
                "evidence_refs": [],
            }

        estimated_cost = float(metadata.get("estimated_cost_usd", 0.0))
        if estimated_cost > 0 and not self.permission_engine.charge(estimated_cost):
            reason = "Blocked: budget guard rejected charge."
            self.audit_logger.log(
                action=action,
                tool=tool_name,
                inputs=inputs,
                outcome="blocked",
                allowed=False,
                reason=reason,
            )
            return {
                "success": False,
                "action": action,
                "tool": tool_name,
                "outcome": reason,
                "risk_score": risk,
                "confidence": 1.0,
                "evidence_refs": [],
            }

        try:
            if risk > 0.0 and metadata.get("modifies_workspace", True):
                raw_paths = metadata.get("target_paths", [])
                if "target_path" in metadata:
                    raw_paths.append(metadata["target_path"])
                paths_to_backup = [Path(p) for p in raw_paths] if raw_paths else []
                self.rollback_manager.create_checkpoint(paths_to_backup)
            output = execute()
            if isinstance(output, dict):
                outcome_text = str(output.get("outcome", output))
                confidence = float(output.get("confidence", 0.8))
                evidence_refs = list(output.get("evidence_refs", []))
            else:
                outcome_text = str(output)
                confidence = 0.8
                evidence_refs = []
            self.audit_logger.log(
                action=action,
                tool=tool_name,
                inputs=inputs,
                outcome="success",
                allowed=True,
            )
            return {
                "success": True,
                "action": action,
                "tool": tool_name,
                "outcome": outcome_text,
                "confidence": confidence,
                "evidence_refs": evidence_refs,
                "risk_score": risk,
            }
        except Exception as exc:
            self.audit_logger.log(
                action=action,
                tool=tool_name,
                inputs=inputs,
                outcome="failed",
                allowed=True,
                reason=str(exc),
            )
            return {
                "success": False,
                "action": action,
                "tool": tool_name,
                "outcome": f"Execution failed: {exc}",
                "risk_score": risk,
                "confidence": 0.2,
                "evidence_refs": [],
            }
