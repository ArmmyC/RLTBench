from __future__ import annotations

import time
from typing import Any

import httpx

from rtlbench.types import GenerationResult


class OpenAICompatibleClient:
    def __init__(self, base_url: str, api_key: str, timeout: float, retries: int = 2):
        self.base_url = base_url.rstrip("/")
        self.retries = retries
        self.client = httpx.Client(
            timeout=timeout,
            headers={"Authorization": f"Bearer {api_key}"},
        )

    def close(self) -> None:
        self.client.close()

    def generate(
        self,
        *,
        model: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        top_p: float,
        max_tokens: int,
        extra_body: dict[str, Any] | None = None,
    ) -> GenerationResult:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "top_p": top_p,
            "max_tokens": max_tokens,
        }
        if extra_body:
            payload.update(extra_body)
        started = time.monotonic()
        last_error: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                response = self.client.post(f"{self.base_url}/chat/completions", json=payload)
                response.raise_for_status()
                body: dict[str, Any] = response.json()
                text = body["choices"][0]["message"]["content"] or ""
                return GenerationResult(
                    text=text,
                    latency_seconds=time.monotonic() - started,
                    usage=body.get("usage"),
                )
            except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
                last_error = exc
                if attempt < self.retries:
                    time.sleep(2**attempt)
        raise RuntimeError(f"Model request failed after {self.retries + 1} attempts: {last_error}")
