from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .parsing import ToolCall


class RunLogger:
    def __init__(self, log_dir: Path) -> None:
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        self.path = log_dir / f"hello_ticket_{timestamp}.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._file = self.path.open("w", encoding="utf-8")

    def log_event(self, event: str, payload: Dict[str, Any]) -> None:
        record = {"type": event, **payload}
        self._file.write(json.dumps(record, ensure_ascii=False) + "\n")
        self._file.flush()

    def log_turn(
        self,
        turn_index: int,
        agent: str,
        message: str,
        tool_calls: List[ToolCall],
        tool_outputs: List[Dict[str, Any]],
        usage: Optional[Dict[str, Any]],
    ) -> None:
        payload: Dict[str, Any] = {
            "turn": turn_index,
            "agent": agent,
            "message": message,
            "tool_calls": [
                {"name": call.name, "arguments": call.arguments} for call in tool_calls
            ],
            "tool_outputs": tool_outputs,
        }
        if usage:
            usage_dict: Dict[str, Any]
            if hasattr(usage, "model_dump"):
                usage_dict = usage.model_dump()
            elif hasattr(usage, "to_dict"):
                usage_dict = usage.to_dict()  # type: ignore[assignment]
            else:
                usage_dict = dict(usage.__dict__)
            payload["usage"] = usage_dict
        self.log_event("turn", payload)

    def close(self) -> None:
        self._file.close()
