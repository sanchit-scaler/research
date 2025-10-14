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
from orchestrator.prompts import (
    ALEX_OPERATIONS_PERSONA,
    ENGINEER_PERSONA,
    ENGINEER_SYSTEM_PROMPT,
    HELLO_TICKET_WORLD,
    JORDAN_PRODUCT_OPS_PERSONA,
    PLANNER_PERSONA,
    PLANNER_SYSTEM_PROMPT,
    SAM_ENGINEERING_PERSONA,
    TAYLOR_ANALYST_PERSONA,
    TOOL_INTEGRATION_WORLD,
    build_agent_prompt,
    extract_scenario_name,
)


console = Console()


def _build_run_signature(cfg: Config, world_prompt: str, agent_personas: Dict[str, str], composed_prompts: Dict[str, str]) -> Dict[str, Any]:
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
            "max_tool_rounds": cfg.run.max_tool_rounds,
            "log_dir": str(cfg.run.log_dir),
        },
        "world_prompt": world_prompt,
        "agent_personas": agent_personas,
        "composed_prompts": composed_prompts,
    }


async def main(world_prompt: str = HELLO_TICKET_WORLD) -> None:
    """Run the orchestrator with a given world/scenario prompt.
    
    Args:
        world_prompt: The scenario/world context to use. Defaults to HELLO_TICKET_WORLD.
    """
    cfg = load_config()
    
    # Determine if this is a 4-agent scenario (tool integration) or 2-agent scenario
    is_four_agent = world_prompt == TOOL_INTEGRATION_WORLD
    
    if is_four_agent:
        # 4-agent team: Alex, Sam, Jordan, Taylor
        alex_prompt = build_agent_prompt(world_prompt, ALEX_OPERATIONS_PERSONA)
        sam_prompt = build_agent_prompt(world_prompt, SAM_ENGINEERING_PERSONA)
        jordan_prompt = build_agent_prompt(world_prompt, JORDAN_PRODUCT_OPS_PERSONA)
        taylor_prompt = build_agent_prompt(world_prompt, TAYLOR_ANALYST_PERSONA)
        
        agent_personas = {
            "alex": ALEX_OPERATIONS_PERSONA,
            "sam": SAM_ENGINEERING_PERSONA,
            "jordan": JORDAN_PRODUCT_OPS_PERSONA,
            "taylor": TAYLOR_ANALYST_PERSONA,
        }
        composed_prompts = {
            "alex": alex_prompt,
            "sam": sam_prompt,
            "jordan": jordan_prompt,
            "taylor": taylor_prompt,
        }
    else:
        # 2-agent team: Planner, Engineer (original)
        planner_prompt = build_agent_prompt(world_prompt, PLANNER_PERSONA)
        engineer_prompt = build_agent_prompt(world_prompt, ENGINEER_PERSONA)
        
        agent_personas = {
            "planner": PLANNER_PERSONA,
            "engineer": ENGINEER_PERSONA,
        }
        composed_prompts = {
            "planner": planner_prompt,
            "engineer": engineer_prompt,
        }
    
    # Build run signature with configuration details
    run_signature = _build_run_signature(cfg, world_prompt, agent_personas, composed_prompts)
    
    # Extract scenario name for log filename
    scenario_name = extract_scenario_name(world_prompt)
    
    logger = RunLogger(cfg.run.log_dir, run_signature=run_signature, scenario_name=scenario_name)
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

        # Create agents based on configuration
        if is_four_agent:
            alex = AgentState("alex", _build_prompt(alex_prompt, tools))
            sam = AgentState("sam", _build_prompt(sam_prompt, tools))
            jordan = AgentState("jordan", _build_prompt(jordan_prompt, tools))
            taylor = AgentState("taylor", _build_prompt(taylor_prompt, tools))
            agents = [alex, sam, jordan, taylor]
            num_agents = 4
        else:
            planner = AgentState("planner", _build_prompt(composed_prompts["planner"], tools))
            engineer = AgentState("engineer", _build_prompt(composed_prompts["engineer"], tools))
            agents = [planner, engineer]
            num_agents = 2

        for turn in range(cfg.run.max_turns):
            active = agents[turn % num_agents]
            # Get all teammates (everyone except active agent)
            teammates = [a for a in agents if a != active]
            
            console.print(f"\n[bold magenta]Turn {turn + 1} — {active.name.capitalize()}[/]")
            
            # Check if this is a reflection turn
            should_reflect = (turn + 1) % cfg.run.reflection_interval == 0
            if should_reflect and turn > 0:  # Don't reflect on first turn
                reflection_prompt = (
                    "Please take a moment to reflect on progress so far. "
                    "What has been accomplished? What are the next steps? "
                    "Are there any blockers or concerns?"
                )
                active.receive(reflection_prompt)
                console.print(f"[yellow]↻ Reflection prompt injected[/]")

            message, tool_calls, tool_outputs, usage = await _drive_agent_turn(
                active,
                teammates,
                llm,
                mcp,
                max_tool_rounds=cfg.run.max_tool_rounds,
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
    teammates: List[AgentState],
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
                # Output message already persisted via add_output_items; broadcast to all teammates
                for teammate in teammates:
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
                # Notify all teammates with concise summary
                for teammate in teammates:
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
                # Send a short summary to all teammates to keep them aware
                summary = (output_str or "(no content)").strip()
                summary = " ".join(summary.split())
                for teammate in teammates:
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
                for teammate in teammates:
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
