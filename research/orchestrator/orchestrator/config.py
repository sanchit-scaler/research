from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


@dataclass(slots=True)
class OpenAIConfig:
    api_key: str
    model: str = "gpt-4o-mini"
    temperature: float = 0.3
    seed: Optional[int] = None


@dataclass(slots=True)
class MCPServerConfig:
    smartsheet_cmd: str = (
        "python /Users/apple/Github/mcp-ai-lab/smartsheet/main_mcp.py"
    )
    linear_cmd: str = (
        "uv --directory /Users/apple/Github/mimicry-club run python -m apps.linear.mcp"
    )


@dataclass(slots=True)
class RunConfig:
    max_turns: int = 40
    stale_turn_limit: int = 6
    reflection_interval: int = 8
    max_tool_rounds: int = 8
    log_dir: Path = Path("runs")
    
    @staticmethod
    def from_env() -> "RunConfig":
        """Load run configuration from environment variables with defaults."""
        max_turns = int(os.getenv("MAX_TURNS", "40"))
        stale_turn_limit = int(os.getenv("STALE_TURN_LIMIT", "6"))
        reflection_interval = int(os.getenv("REFLECTION_INTERVAL", "8"))
        max_tool_rounds = int(os.getenv("MAX_TOOL_ROUNDS", "8"))
        log_dir_str = os.getenv("LOG_DIR", "runs")
        log_dir = Path(log_dir_str)
        
        return RunConfig(
            max_turns=max_turns,
            stale_turn_limit=stale_turn_limit,
            reflection_interval=reflection_interval,
            max_tool_rounds=max_tool_rounds,
            log_dir=log_dir,
        )


@dataclass(slots=True)
class Config:
    openai: OpenAIConfig
    mcp: MCPServerConfig
    run: RunConfig


def load_config() -> Config:
    load_dotenv()

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required (set in .env)")

    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.3"))
    seed_val = os.getenv("OPENAI_SEED")
    seed = int(seed_val) if seed_val else None

    smartsheet_cmd = os.getenv(
        "SMARTSHEET_MCP_CMD",
        "python /Users/apple/Github/mcp-ai-lab/smartsheet/main_mcp.py",
    )
    linear_cmd = os.getenv(
        "LINEAR_MCP_CMD",
        "uv --directory /Users/apple/Github/mimicry-club run python -m apps.linear.mcp",
    )

    openai_cfg = OpenAIConfig(
        api_key=api_key,
        model=model,
        temperature=temperature,
        seed=seed,
    )
    mcp_cfg = MCPServerConfig(
        smartsheet_cmd=smartsheet_cmd,
        linear_cmd=linear_cmd,
    )
    run_cfg = RunConfig.from_env()

    run_cfg.log_dir.mkdir(parents=True, exist_ok=True)

    return Config(openai=openai_cfg, mcp=mcp_cfg, run=run_cfg)
