"""Governance behavior tests."""

from __future__ import annotations

from pathlib import Path

from executor.safe_runner import SafeRunner
from governance.audit_logger import AuditLogger
from governance.permission_engine import PermissionEngine


def test_governance_blocks_risky_actions_by_default(tmp_path: Path) -> None:
    permissions = PermissionEngine(
        config={
            "allow_shell": False,
            "allow_file_write_outside_workspace": False,
            "allow_os_automation": False,
            "allow_network": False,
            "require_confirmation_for": [
                "cloud_deploy",
                "file_delete",
                "install_software",
                "login",
                "payment",
            ],
            "max_daily_budget_usd": 0,
        }
    )
    audit = AuditLogger(tmp_path / "audit.jsonl")
    runner = SafeRunner(
        permission_engine=permissions,
        audit_logger=audit,
        workspace_dir=tmp_path,
    )
    result = runner.run(
        action="shell execute",
        tool_name="shell_tool",
        inputs={"command": "echo hello"},
        metadata={},
        execute=lambda: "ok",
    )

    assert result["success"] is False
    assert "blocked" in str(result["outcome"]).lower()
    assert Path(tmp_path / "audit.jsonl").exists()


def test_governance_blocks_network_and_os_automation_by_default(tmp_path: Path) -> None:
    permissions = PermissionEngine(
        config={
            "allow_shell": False,
            "allow_file_write_outside_workspace": False,
            "allow_os_automation": False,
            "allow_network": False,
            "require_confirmation_for": [],
            "max_daily_budget_usd": 0,
        }
    )
    audit = AuditLogger(tmp_path / "audit2.jsonl")
    runner = SafeRunner(
        permission_engine=permissions,
        audit_logger=audit,
        workspace_dir=tmp_path,
    )

    network_block = runner.run(
        action="browser fetch page",
        tool_name="browser_tool",
        inputs={"url": "https://example.com"},
        metadata={"requires_network": True},
        execute=lambda: "network-call",
    )
    os_block = runner.run(
        action="os_automation click",
        tool_name="input_tool",
        inputs={"x": 10, "y": 10},
        metadata={},
        execute=lambda: "click",
    )

    assert network_block["success"] is False
    assert "network" in str(network_block["outcome"]).lower()
    assert os_block["success"] is False
    assert "os automation" in str(os_block["outcome"]).lower()
