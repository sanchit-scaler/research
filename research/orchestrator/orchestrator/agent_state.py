from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


Message = Dict[str, str]


@dataclass
class AgentState:
    name: str
    system_prompt: str
    # Mixed list: regular chat messages and Responses API items (e.g., function_call)
    inputs: List[Any] = field(default_factory=list)
    stale_turns: int = 0

    def build_messages(self) -> List[Message]:
        # Backwards compat for simple text-only completions
        return [{"role": "system", "content": self.system_prompt}, *self.inputs]  # type: ignore[list-item]

    def build_inputs(self) -> List[Any]:
        """Return inputs suitable for the Responses API (mixed types)."""
        return [{"role": "system", "content": self.system_prompt}, *self.inputs]

    def receive(self, content: str) -> None:
        """Append a user message (from the teammate)."""
        if content.strip():
            self.inputs.append({"role": "user", "content": content.strip()})

    def respond(self, content: str) -> None:
        if content.strip():
            self.inputs.append({"role": "assistant", "content": content.strip()})

    def add_output_items(self, items: List[Any]) -> None:
        """Append raw response.output items (e.g., reasoning, function_call)."""
        if items:
            self.inputs.extend(items)

    def add_function_output(self, call_id: str, output: str) -> None:
        """Append a function_call_output item linked to a prior call_id."""
        self.inputs.append(
            {
                "type": "function_call_output",
                "call_id": call_id,
                "output": output,
            }
        )

    def reset_stale(self) -> None:
        self.stale_turns = 0

    def increment_stale(self) -> None:
        self.stale_turns += 1
