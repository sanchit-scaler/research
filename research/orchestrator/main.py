from __future__ import annotations

import asyncio
import os
from datetime import datetime
from typing import Any, Dict, List

from rich.console import Console

from orchestrator.agent_state import AgentState
from orchestrator.config import Config, load_config
from orchestrator.llm import OpenAIClient
from orchestrator.logger import RunLogger
from orchestrator.mcp_manager import MCPManager, NamespacedTool
from orchestrator.parsing import ToolCall
from orchestrator.prompts import ENGINEER_SYSTEM_PROMPT, PLANNER_SYSTEM_PROMPT


console = Console()


def _build_run_signature(cfg: Config) -> Dict[str, Any]:
    """Build a run signature containing configuration and prompts for this run."""
    return {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "environment": {
            "openai_api_key": "***" if cfg.openai.api_key else None,
            "openai_model": cfg.openai.model,
            "openai_temperature": cfg.openai.temperature,
            "openai_seed": cfg.openai.seed,
            "smartsheet_mcp_cmd": cfg.mcp.smartsheet_cmd,
            "linear_mcp_cmd": cfg.mcp.linear_cmd,
        },
        "run_config": {
            "max_turns": cfg.run.max_turns,
            "stale_turn_limit": cfg.run.stale_turn_limit,
            "reflection_interval": cfg.run.reflection_interval,
            "log_dir": str(cfg.run.log_dir),
        },
        "agent_prompts": {
            "planner": PLANNER_SYSTEM_PROMPT,
            "engineer": ENGINEER_SYSTEM_PROMPT,
        },
    }


async def main() -> None:
    cfg = load_config()
    
    # Build run signature with configuration details
    run_signature = _build_run_signature(cfg)
    
    logger = RunLogger(cfg.run.log_dir, run_signature=run_signature)
    mcp = MCPManager(cfg.mcp)
    llm = OpenAIClient(cfg.openai)

    console.print("[bold cyan]Connecting to MCP servers...[/]")
    try:
        tools = await mcp.connect_all()
        logger.log_event(
            "tools_discovered",
            {"tools": [tool.fq_name for tool in tools]},
        )

        console.print("[green]Connected. Available tools:[/]")
        for tool in tools:
            console.print(f"  • {tool.describe()}")

        console.print("[bold cyan]Performing health probes...[/]")
        health = await mcp.health_probe()
        for name, result in health.items():
            console.print(f"  {name}: {result}")
        logger.log_event("health_probe", {"results": health})

        planner_prompt = _build_prompt(PLANNER_SYSTEM_PROMPT, tools)
        engineer_prompt = _build_prompt(ENGINEER_SYSTEM_PROMPT, tools)

        planner = AgentState("planner", planner_prompt)
        engineer = AgentState("engineer", engineer_prompt)
        agents = [planner, engineer]

        for turn in range(cfg.run.max_turns):
            active = agents[turn % 2]
            teammate = agents[(turn + 1) % 2]
            console.print(f"\n[bold magenta]Turn {turn + 1} — {active.name.capitalize()}[/]")

            message, tool_calls, tool_outputs, usage = await _drive_agent_turn(
                active,
                teammate,
                llm,
                mcp,
                max_tool_rounds=6,
            )

            logger.log_turn(
                turn_index=turn + 1,
                agent=active.name,
                message=message,
                tool_calls=tool_calls,
                tool_outputs=tool_outputs,
                usage=usage,
            )

            # If a finish tool was invoked, end the run immediately
            if message == "__RUN_FINISHED__":
                console.print("\n[bold green]Run finished by agent.[/]")
                break

            activity = bool(tool_calls) or bool(message and message.strip())
            if activity:
                active.reset_stale()
            else:
                active.increment_stale()

            if active.stale_turns >= cfg.run.stale_turn_limit:
                console.print(
                    f"[yellow]{active.name} reached stale limit ({cfg.run.stale_turn_limit}). Stopping.[/]"
                )
                break

        console.print("\n[bold green]Run complete.[/]")
    finally:
        try:
            await mcp.close()
        except asyncio.CancelledError:
            pass
        logger.close()


def _build_prompt(base_prompt: str, tools: List[NamespacedTool]) -> str:
    tool_text = "\n".join(tool.describe() for tool in tools)
    return (
        f"{base_prompt}\n\n"
        "Available MCP tools:\n"
        f"{tool_text}\n"
        "Tools are provided as callable functions; use them when needed.\n"
        "If no tool is needed, reply with concise natural language."
    )


async def _drive_agent_turn(
    agent: AgentState,
    teammate: AgentState,
    llm: OpenAIClient,
    mcp: MCPManager,
    *,
    max_tool_rounds: int,
):
    accumulated_tool_calls: List[ToolCall] = []
    tool_outputs: List[dict] = []
    usage = None

    # Convert MCP tools to OpenAI tools once per turn
    oi_tools = mcp.openai_tools()

    inputs = agent.build_inputs()
    rounds = 0
    while rounds < max_tool_rounds:
        rounds += 1
        response = await llm.respond_with_tools(
            inputs,
            tools=oi_tools,
            parallel_tool_calls=False,
            tool_choice="auto",
        )

        usage = getattr(response, "usage", None)

        # Persist raw output items (reasoning/function_call/message) to agent
        try:
            output_items = list(response.output)
        except Exception:
            output_items = []
        if output_items:
            agent.add_output_items(output_items)
            inputs.extend(output_items)

        # Collect function calls
        tool_calls = []
        for item in output_items:
            if getattr(item, "type", None) == "function_call":
                tool_calls.append(item)

        if not tool_calls:
            # No tool calls, extract natural language if present
            natural_text = _extract_message_text(response)
            if natural_text:
                console.print(f"[cyan]{agent.name}:[/] {natural_text}")
                # Output message already persisted via add_output_items; just notify teammate
                teammate.receive(f"{agent.name}: {natural_text}")
            return natural_text, accumulated_tool_calls, tool_outputs, usage

        # Execute each tool call serially
        for fc in tool_calls:
            name = getattr(fc, "name", "")
            args_json = getattr(fc, "arguments", "{}")
            call_id = getattr(fc, "call_id", None)

            try:
                fq = mcp.resolve_openai_tool_name(name)
            except KeyError:
                fq = name  # fallback

            try:
                import json as _json

                arguments = _json.loads(args_json) if isinstance(args_json, str) else (args_json or {})
            except Exception:
                arguments = {}

            # Handle synthetic finish tool locally
            if name in ("orchestrator__finish",) or fq in ("orchestrator.finish",):
                summary = arguments.get("summary", "Run finished.") if isinstance(arguments, dict) else "Run finished."
                console.print(f"[green]↳ Finish:[/] {summary}")
                if call_id:
                    agent.add_function_output(call_id, "finished")
                    inputs.append({"type": "function_call_output", "call_id": call_id, "output": "finished"})
                # Log as a tool call/output for consistency
                accumulated_tool_calls.append(ToolCall(name="orchestrator.finish", arguments=arguments if isinstance(arguments, dict) else {}))
                tool_outputs.append({"name": "orchestrator.finish", "arguments": arguments, "output": "finished"})
                # Notify teammate with concise summary
                teammate.receive(f"{agent.name} finished: {summary}")
                return "__RUN_FINISHED__", accumulated_tool_calls, tool_outputs, usage

            # Log to console
            console.print(f"[blue]→ {fq} {arguments}[/]")

            try:
                rendered, raw = await mcp.call(fq, arguments)
                console.print(
                    f"[blue]← {rendered}[/]" if rendered else "[blue]← (no content)[/]"
                )
                tool_outputs.append(
                    {"name": fq, "arguments": arguments, "output": rendered}
                )
                accumulated_tool_calls.append(
                    ToolCall(name=fq, arguments=arguments)
                )
                # Provide tool output to the model
                output_str = rendered if isinstance(rendered, str) else str(rendered)
                if call_id:
                    agent.add_function_output(call_id, output_str)
                    inputs.append(
                        {
                            "type": "function_call_output",
                            "call_id": call_id,
                            "output": output_str,
                        }
                    )
                # Send a short summary to teammate to keep them aware
                summary = (output_str or "(no content)").strip()
                summary = " ".join(summary.split())
                teammate.receive(
                    f"{agent.name} tool {fq}: {summary[:400]}"
                )
            except Exception as exc:  # noqa: BLE001
                error_message = f"[tool-error:{fq}] {exc}"
                console.print(f"[red]{error_message}[/]")
                tool_outputs.append(
                    {
                        "name": fq,
                        "arguments": arguments,
                        "error": str(exc),
                    }
                )
                if call_id:
                    agent.add_function_output(call_id, str(exc))
                    inputs.append(
                        {
                            "type": "function_call_output",
                            "call_id": call_id,
                            "output": str(exc),
                        }
                    )
                teammate.receive(f"{agent.name} tool {fq} failed: {exc}")

    console.print(
        "[red]Max tool rounds reached without natural response; handing over turn.[/]"
    )
    return "", accumulated_tool_calls, tool_outputs, usage


def _extract_message_text(response) -> str:
    try:
        parts = []
        for block in response.output:
            if getattr(block, "type", None) != "message":
                continue
            for item in getattr(block, "content", []):
                if getattr(item, "type", None) == "output_text":
                    parts.append(getattr(item, "text", ""))
        return "\n".join(p for p in parts if p).strip()
    except Exception:
        return ""


if __name__ == "__main__":
    asyncio.run(main())
