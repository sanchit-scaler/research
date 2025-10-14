from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


Message = Dict[str, str]


@dataclass
class AgentState:
    name: str
    system_prompt: str
    history: List[Message] = field(default_factory=list)
    stale_turns: int = 0

    def build_messages(self) -> List[Message]:
        return [{"role": "system", "content": self.system_prompt}, *self.history]

    def receive(self, content: str) -> None:
        """Append a user message (from the teammate)."""
        if content.strip():
            self.history.append({"role": "user", "content": content.strip()})

    def respond(self, content: str) -> None:
        if content.strip():
            self.history.append({"role": "assistant", "content": content.strip()})

    def reset_stale(self) -> None:
        self.stale_turns = 0

    def increment_stale(self) -> None:
        self.stale_turns += 1
