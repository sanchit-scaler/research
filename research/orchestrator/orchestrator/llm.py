from __future__ import annotations

from typing import Any, Dict, List, Tuple

from openai import AsyncOpenAI, BadRequestError

from .config import OpenAIConfig


class OpenAIClient:
    """Thin wrapper around the OpenAI Responses API."""

    def __init__(self, cfg: OpenAIConfig) -> None:
        self._client = AsyncOpenAI(api_key=cfg.api_key)
        self._model = cfg.model
        self._temperature = cfg.temperature
        self._seed = cfg.seed
        self._temperature_supported = cfg.temperature is not None

    async def complete(
        self, messages: List[Dict[str, Any]], max_output_tokens: int = 600
    ) -> Tuple[str, Dict[str, Any]]:
        kwargs: Dict[str, Any] = {
            "model": self._model,
            "input": messages,
            "max_output_tokens": max_output_tokens,
        }
        include_temp = self._should_include_temperature()
        if include_temp:
            kwargs["temperature"] = self._temperature
        if self._seed is not None:
            kwargs["seed"] = self._seed

        try:
            response = await self._client.responses.create(**kwargs)
        except BadRequestError as err:
            if self._handle_temperature_error(err, include_temp):
                kwargs.pop("temperature", None)
                response = await self._client.responses.create(**kwargs)
            else:
                raise

        text = getattr(response, "output_text", None)
        if text is None:
            text = _extract_text(response)

        usage = getattr(response, "usage", {})
        return text.strip(), usage

    async def respond_with_tools(
        self,
        inputs: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        *,
        max_output_tokens: int = 600,
        parallel_tool_calls: bool = False,
        tool_choice: Any = "auto",
    ) -> Any:
        """Call the Responses API with tool definitions and mixed inputs.

        Returns the raw response object so callers can inspect tool calls.
        """
        kwargs: Dict[str, Any] = {
            "model": self._model,
            "input": inputs,
            "tools": tools,
            "max_output_tokens": max_output_tokens,
            "parallel_tool_calls": parallel_tool_calls,
            "tool_choice": tool_choice,
        }
        include_temp = self._should_include_temperature()
        if include_temp:
            kwargs["temperature"] = self._temperature
        if self._seed is not None:
            kwargs["seed"] = self._seed

        try:
            return await self._client.responses.create(**kwargs)
        except BadRequestError as err:
            if self._handle_temperature_error(err, include_temp):
                kwargs.pop("temperature", None)
                return await self._client.responses.create(**kwargs)
            raise

    def _should_include_temperature(self) -> bool:
        return self._temperature is not None and self._temperature_supported

    def _handle_temperature_error(self, err: BadRequestError, attempted_with_temp: bool) -> bool:
        if not attempted_with_temp:
            return False
        message = ""
        if hasattr(err, "body") and isinstance(err.body, dict):
            message = err.body.get("error", {}).get("message", "")
        if not message:
            message = str(err)
        if "Unsupported parameter" in message and "temperature" in message:
            self._temperature_supported = False
            return True
        return False


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
