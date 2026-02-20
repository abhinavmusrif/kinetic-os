"""Structured JSONL audit logger."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class AuditLogger:
    """Writes action audit records as JSON lines."""

    def __init__(self, log_path: Path) -> None:
        self.log_path = log_path
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger("ao.audit")
        self.logger.setLevel(logging.INFO)

    @staticmethod
    def _hash_inputs(inputs: dict[str, Any]) -> str:
        payload = json.dumps(inputs, sort_keys=True, default=str).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def log(
        self,
        action: str,
        tool: str,
        inputs: dict[str, Any],
        outcome: str,
        allowed: bool,
        reason: str = "",
    ) -> None:
        """Append one JSONL audit event."""
        event = {
            "timestamp": datetime.now(UTC).isoformat(),
            "action": action,
            "tool": tool,
            "inputs_hash": self._hash_inputs(inputs),
            "outcome": outcome,
            "allowed": allowed,
            "reason": reason,
        }
        with self.log_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, ensure_ascii=True) + "\n")
        self.logger.info(json.dumps(event, ensure_ascii=True))
