"""Anthropic EU client — the MVP LLM provider (ADR-0010).

Data residency is EU at the account level. Not exercised when no key is configured; the
callers fall back to deterministic offline paths (ADR-0014), so the slice never makes a US
LLM call by default.
"""

from __future__ import annotations

from typing import Any

import httpx

from app.llm.base import LLMError


class AnthropicEUClient:
    def __init__(
        self,
        api_key: str,
        model: str,
        client: httpx.AsyncClient,
        *,
        base_url: str = "https://api.anthropic.com",
    ) -> None:
        self._key = api_key
        self._model = model
        self._http = client
        self._url = base_url.rstrip("/") + "/v1/messages"

    async def complete(self, system: str, prompt: str, *, max_tokens: int = 1024) -> str:
        headers = {
            "x-api-key": self._key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        body: dict[str, Any] = {
            "model": self._model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": prompt}],
        }
        try:
            resp = await self._http.post(self._url, json=body, headers=headers)
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise LLMError(f"anthropic request failed: {exc}") from exc
        data = resp.json()
        blocks = data.get("content", [])
        text = "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
        if not text:
            raise LLMError("anthropic returned no text content")
        return text
