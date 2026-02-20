"""Top-level application orchestrator."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.control_loop import ControlLoop
from core.event_bus import EventBus
from core.policy_runtime import ensure_runtime_dirs, load_effective_config
from core.state_manager import StateManager
from executor.action_router import ActionRouter
from executor.safe_runner import SafeRunner
from governance.audit_logger import AuditLogger
from governance.permission_engine import PermissionEngine
from llm.llm_factory import build_llm
from memory.consolidation.consolidator import Consolidator
from memory.memory_manager import MemoryManager
from memory.retrieval import MemoryRetriever
from memory.stores.sql_store import SQLStore
from planner.task_decomposer import TaskDecomposer
from tools.tool_registry import build_default_registry


@dataclass
class RuntimeBundle:
    """Holds initialized runtime components."""

    config: dict[str, Any]
    memory: MemoryManager
    llm: Any
    control_loop: ControlLoop
    consolidator: Consolidator
    permissions: PermissionEngine
    tool_registry: Any


class Orchestrator:
    """Creates and wires runtime components for CLI use."""

    def __init__(self, root: Path | None = None) -> None:
        default_root = Path(__file__).resolve().parents[1]
        self.root = (root or default_root).resolve()

    def build(self) -> RuntimeBundle:
        config = load_effective_config(self.root)
        paths = ensure_runtime_dirs(self.root, config)

        sql_store = SQLStore(paths["db_path"])
        sql_store.create_all()

        memory = MemoryManager(
            sql_store=sql_store,
            context_limit=int(config.get("memory", {}).get("context_buffer_limit", 30)),
        )
        retriever = MemoryRetriever(memory_manager=memory)
        llm = build_llm(config=config)

        permissions = PermissionEngine(config=self._permissions(config))
        audit_logger = AuditLogger(paths["audit_log_path"])
        safe_runner = SafeRunner(
            permission_engine=permissions,
            audit_logger=audit_logger,
            workspace_dir=paths["workspace_dir"],
        )
        tool_registry = build_default_registry(
            root=self.root,
            workspace_dir=paths["workspace_dir"],
            config=config.get("tools_cfg", {}),
            safe_runner=safe_runner,
        )
        action_router = ActionRouter(tool_registry=tool_registry)
        control_loop = ControlLoop(
            event_bus=EventBus(),
            task_decomposer=TaskDecomposer(llm=llm),
            action_runner=action_router,
            memory_manager=memory,
        )
        consolidator = Consolidator(memory_manager=memory, llm_provider=llm)

        # Keep recently retrieved context for optional prompt injection.
        memory.retriever = retriever
        StateManager()  # Instantiated for future state extensions.

        return RuntimeBundle(
            config=config,
            memory=memory,
            llm=llm,
            control_loop=control_loop,
            consolidator=consolidator,
            permissions=permissions,
            tool_registry=tool_registry,
        )

    @staticmethod
    def _permissions(config: dict[str, Any]) -> dict[str, Any]:
        return dict(config.get("permissions", {}))
