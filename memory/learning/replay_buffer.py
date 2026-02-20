"""Replay buffer scaffold."""

from __future__ import annotations

from collections import deque
from typing import Any


class ReplayBuffer:
    """Small replay buffer for learning experiments."""

    def __init__(self, maxlen: int = 128) -> None:
        self._buffer: deque[Any] = deque(maxlen=maxlen)

    def add(self, item: Any) -> None:
        self._buffer.append(item)

    def items(self) -> list[Any]:
        return list(self._buffer)
