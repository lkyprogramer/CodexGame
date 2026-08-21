from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


@dataclass
class ChatResponse:
    message: dict[str, Any]
    usage: dict[str, Any]
    raw: dict[str, Any]


class OpenAICompatibleClient:
    def __init__(self, base_url: str, api_key: str, timeout_seconds: float):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    def chat(
        self,
        *,
        model: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
        temperature: float,
        top_p: float,
        top_k: int,
        min_p: float,
        max_tokens: int,
        seed: int,
        reasoning_effort: str | None,
        extra_body: dict[str, Any] | None = None,
    ) -> ChatResponse:
        body: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "top_p": top_p,
            "max_tokens": max_tokens,
            "seed": seed,
            "stream": False,
        }
        if top_k > 0:
            body["top_k"] = top_k
        if min_p > 0:
            body["min_p"] = min_p
        if reasoning_effort:
            body["reasoning_effort"] = reasoning_effort
        if tools:
            body["tools"] = tools
            body["tool_choice"] = "auto"
        if extra_body:
            body.update(extra_body)

        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Endpoint returned HTTP {exc.code}: {details}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Endpoint request failed: {exc}") from exc

        choices = payload.get("choices") or []
        if not choices:
            raise RuntimeError(f"Endpoint response has no choices: {payload}")
        message = choices[0].get("message") or {}
        return ChatResponse(message=message, usage=payload.get("usage") or {}, raw=payload)
