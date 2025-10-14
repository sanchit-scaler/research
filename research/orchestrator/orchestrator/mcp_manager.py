from __future__ import annotations

import asyncio
import shlex
from contextlib import AsyncExitStack
from dataclasses import dataclass
from typing import Dict, List, Mapping, Optional, Tuple

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import CallToolResult, TextContent, Tool

from .config import MCPServerConfig


@dataclass(slots=True)
class NamespacedTool:
    namespace: str
    definition: Tool

    @property
    def fq_name(self) -> str:
        return f"{self.namespace}.{self.definition.name}"

    def describe(self) -> str:
        desc = self.definition.description or ""
        return f"- {self.fq_name}: {desc}"


class MCPServerHandle:
    def __init__(self, namespace: str, command: str) -> None:
        self.namespace = namespace
        self.command = command
        self._exit_stack: Optional[AsyncExitStack] = None
        self._session: Optional[ClientSession] = None

    async def connect(self) -> List[ToolDefinition]:
        if self._session:
            return []

        self._exit_stack = AsyncExitStack()
        cmd_parts = shlex.split(self.command)
        if not cmd_parts:
            raise RuntimeError(f"Empty command for namespace '{self.namespace}'")

        params = _build_stdio_params(cmd_parts)
        transport = await self._exit_stack.enter_async_context(stdio_client(params))
        reader, writer = transport
        self._session = await self._exit_stack.enter_async_context(
            ClientSession(reader, writer)
        )

        await self._session.initialize()
        response = await self._session.list_tools()
        return response.tools

    async def close(self) -> None:
        if self._exit_stack:
            try:
                await self._exit_stack.aclose()
            except (RuntimeError, asyncio.CancelledError):
                # Ignore cancellation noise during shutdown
                pass
        self._exit_stack = None
        self._session = None

    async def call_tool(self, name: str, arguments: Mapping[str, object]) -> CallToolResult:
        if not self._session:
            raise RuntimeError(f"MCP server '{self.namespace}' is not connected")
        return await self._session.call_tool(name, dict(arguments))


class MCPManager:
    def __init__(self, cfg: MCPServerConfig) -> None:
        self._servers = {
            "smartsheet": MCPServerHandle("smartsheet", cfg.smartsheet_cmd),
            "linear": MCPServerHandle("linear", cfg.linear_cmd),
        }
        self._tools: Dict[str, NamespacedTool] = {}

    async def connect_all(self) -> List[NamespacedTool]:
        tools: List[NamespacedTool] = []
        for namespace, handle in self._servers.items():
            listed = await handle.connect()
            for tool_def in listed:
                ns_tool = NamespacedTool(namespace=namespace, definition=tool_def)
                tools.append(ns_tool)
                self._tools[ns_tool.fq_name] = ns_tool
        return tools

    async def close(self) -> None:
        await asyncio.gather(
            *(handle.close() for handle in self._servers.values()),
            return_exceptions=True,
        )

    async def call(
        self, namespaced_tool: str, arguments: Mapping[str, object]
    ) -> Tuple[str, CallToolResult]:
        namespace, tool_name = self._split_namespace(namespaced_tool)
        handle = self._servers.get(namespace)
        if not handle:
            raise RuntimeError(f"Unknown MCP namespace '{namespace}'")
        result = await handle.call_tool(tool_name, arguments)
        rendered = _render_result(result)
        return rendered, result

    async def health_probe(self) -> Dict[str, str]:
        """Perform lightweight health probes for each server."""
        results: Dict[str, str] = {}
        # Smartsheet health check if available
        if "smartsheet.health_check" in self._tools:
            rendered, _ = await self.call("smartsheet.health_check", {})
            results["smartsheet.health_check"] = rendered
        # Linear list teams if available
        if "linear.list_teams" in self._tools:
            rendered, _ = await self.call("linear.list_teams", {"limit": 1})
            results["linear.list_teams"] = rendered
        return results

    def available_tools(self) -> List[NamespacedTool]:
        return list(self._tools.values())

    @staticmethod
    def _split_namespace(namespaced_tool: str) -> Tuple[str, str]:
        if "." not in namespaced_tool:
            raise ValueError(
                f"Tool '{namespaced_tool}' is missing namespace (expected namespace.tool)"
            )
        namespace, tool_name = namespaced_tool.split(".", 1)
        return namespace, tool_name


def _render_result(result: CallToolResult) -> str:
    if not result.content:
        return ""
    lines = []
    for item in result.content:
        if isinstance(item, TextContent):
            lines.append(item.text)
    return "\n".join(lines)


def _build_stdio_params(cmd_parts: List[str]) -> StdioServerParameters:
    command = cmd_parts[0]
    args = cmd_parts[1:]
    return StdioServerParameters(command=command, args=args, env=None)
