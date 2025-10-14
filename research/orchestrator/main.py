from __future__ import annotations

import asyncio
from typing import List

from rich.console import Console

from orchestrator.agent_state import AgentState
from orchestrator.config import load_config
from orchestrator.llm import OpenAIClient
from orchestrator.logger import RunLogger
from orchestrator.mcp_manager import MCPManager, NamespacedTool
from orchestrator.parsing import ToolCall, extract_tool_calls, strip_tool_call_lines
from orchestrator.prompts import ENGINEER_SYSTEM_PROMPT, PLANNER_SYSTEM_PROMPT


console = Console()


async def main() -> None:
    cfg = load_config()
    logger = RunLogger(cfg.run.log_dir)
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
                max_tool_rounds=3,
            )

            logger.log_turn(
                turn_index=turn + 1,
                agent=active.name,
                message=message,
                tool_calls=tool_calls,
                tool_outputs=tool_outputs,
                usage=usage,
            )

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
        "Always reference tools by their fully-qualified name.\n"
        "If you do not need a tool call, respond with natural language."
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

    for _ in range(max_tool_rounds):
        response_text, usage = await llm.complete(agent.build_messages())
        try:
            tool_calls = extract_tool_calls(response_text)
        except ValueError as exc:
            natural_text = response_text.strip()
            if natural_text:
                console.print(f"[yellow]{agent.name} formatting issue:[/] {exc}")
                agent.respond(natural_text)
                teammate.receive(f"{agent.name}: {natural_text}")
            return natural_text, accumulated_tool_calls, tool_outputs, usage
        natural_text = strip_tool_call_lines(response_text)

        if natural_text:
            console.print(f"[cyan]{agent.name}:[/] {natural_text}")
            agent.respond(natural_text)
            teammate.receive(f"{agent.name}: {natural_text}")

        if not tool_calls:
            return natural_text, accumulated_tool_calls, tool_outputs, usage

        accumulated_tool_calls.extend(tool_calls)

        for call in tool_calls:
            console.print(f"[blue]→ {call.name} {call.arguments}[/]")
            try:
                rendered, raw = await mcp.call(call.name, call.arguments)
                console.print(f"[blue]← {rendered}[/]" if rendered else "[blue]← (no content)[/]")
                tool_outputs.append(
                    {"name": call.name, "arguments": call.arguments, "output": rendered}
                )
                agent.receive(f"[tool:{call.name}] {rendered}")
                summary = (rendered or "(no content)").strip()
                summary = " ".join(summary.split())
                teammate.receive(
                    f"{agent.name} tool {call.name}: {summary[:400]}"  # keep context tight
                )
            except Exception as exc:  # noqa: BLE001
                error_message = f"[tool-error:{call.name}] {exc}"
                console.print(f"[red]{error_message}[/]")
                tool_outputs.append(
                    {
                        "name": call.name,
                        "arguments": call.arguments,
                        "error": str(exc),
                    }
                )
                agent.receive(error_message)
                teammate.receive(f"{agent.name} tool {call.name} failed: {exc}")

    console.print(
        "[red]Max tool rounds reached without natural response; handing over turn.[/]"
    )
    return "", accumulated_tool_calls, tool_outputs, usage


if __name__ == "__main__":
    asyncio.run(main())
