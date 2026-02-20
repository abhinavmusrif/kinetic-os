"""Memory injection helper for prompt augmentation."""

from __future__ import annotations

from typing import Any


def inject_memory(
    messages: list[dict[str, str]],
    retrieved_memories: list[dict[str, Any]],
    max_items: int = 5,
) -> list[dict[str, str]]:
    """Inject condensed memory context into the system prompt."""
    if not retrieved_memories:
        return messages
    snippets = []
    for item in retrieved_memories[:max_items]:
        claim = item.get("claim") or item.get("summary") or str(item)
        confidence = item.get("confidence", "n/a")
        snippets.append(f"- {claim} (confidence={confidence})")
    memory_block = "Relevant memories:\n" + "\n".join(snippets)
    return [{"role": "system", "content": memory_block}, *messages]
