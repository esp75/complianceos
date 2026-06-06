"""LLMProvider interface (the provider-router seam, ADR-0010)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


class LLMError(RuntimeError):
    """Raised on an LLM transport or API error."""


@runtime_checkable
class LLMProvider(Protocol):
    async def complete(self, system: str, prompt: str, *, max_tokens: int = 1024) -> str:
        """Return the model's text completion for a system + user prompt."""
        ...
