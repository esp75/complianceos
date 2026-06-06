"""LLM provider-router (ADR-0010: Claude only for the MVP, Anthropic EU endpoint).

The drafting/extraction code depends on the LLMProvider Protocol, not a concrete client, so
Mistral/self-hosted can slot in post-MVP. When no Anthropic key is configured the app wires
no provider and the callers use their deterministic offline paths (ADR-0014) — so the slice
runs with no key and no US LLM call.
"""

from .base import LLMError, LLMProvider

__all__ = ["LLMError", "LLMProvider"]
