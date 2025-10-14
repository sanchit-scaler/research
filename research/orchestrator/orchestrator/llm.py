from __future__ import annotations

from typing import Any, Dict, List, Tuple

from openai import AsyncOpenAI

from .config import OpenAIConfig


class OpenAIClient:
    """Thin wrapper around the OpenAI Responses API."""

    def __init__(self, cfg: OpenAIConfig) -> None:
        self._client = AsyncOpenAI(api_key=cfg.api_key)
        self._model = cfg.model
        self._temperature = cfg.temperature
        self._seed = cfg.seed

    async def complete(
        self, messages: List[Dict[str, Any]], max_output_tokens: int = 600
    ) -> Tuple[str, Dict[str, Any]]:
        kwargs: Dict[str, Any] = {
            "model": self._model,
            "temperature": self._temperature,
            "input": messages,
            "max_output_tokens": max_output_tokens,
        }
        if self._seed is not None:
            kwargs["seed"] = self._seed

        response = await self._client.responses.create(**kwargs)

        text = getattr(response, "output_text", None)
        if text is None:
            text = _extract_text(response)

        usage = getattr(response, "usage", {})
        return text.strip(), usage


def _extract_text(response: Any) -> str:
    try:
        parts = []
        for block in response.output:
            if block.type != "message":
                continue
            for item in block.content:
                if item.type == "output_text":
                    parts.append(item.text)
        return "\n".join(parts)
    except Exception:
        return str(response)
