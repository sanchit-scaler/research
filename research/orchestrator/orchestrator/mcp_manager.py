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
        # Mapping between OpenAI tool function names and namespaced MCP tool names
        self._openai_name_to_fq: Dict[str, str] = {}

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

    def openai_tools(self) -> List[dict]:
        """Convert discovered MCP tools to OpenAI function tool definitions.

        Returns a list of dicts suitable for the OpenAI Responses API `tools` param.
        Also populates an internal mapping from OpenAI tool names to MCP fq names.
        """
        defs: List[dict] = []
        self._openai_name_to_fq.clear()
        for ns_tool in self.available_tools():
            fq = ns_tool.fq_name  # e.g., "smartsheet.health_check"
            # Sanitize: OpenAI tool names cannot include '.'; map to namespace__name
            sanitized = fq.replace(".", "__")
            self._openai_name_to_fq[sanitized] = fq

            schema = _extract_input_schema(ns_tool.definition)
            defs.append(
                {
                    "type": "function",
                    "name": sanitized,
                    "description": ns_tool.definition.description or "",
                    # Use permissive schema if none provided
                    "parameters": schema
                    if schema is not None
                    else {
                        "type": "object",
                        "properties": {},
                        "additionalProperties": True,
                    },
                }
            )
        # Add a synthetic orchestrator finish tool so agents can explicitly end the run
        finish_name = "orchestrator__finish"
        self._openai_name_to_fq[finish_name] = "orchestrator.finish"
        defs.append(
            {
                "type": "function",
                "name": finish_name,
                "description": "End the run when objectives are complete. Provide a concise summary and relevant links.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "summary": {
                            "type": "string",
                            "description": "One-paragraph summary of what was done and key artifacts (IDs, links).",
                        },
                        "status": {
                            "type": "string",
                            "description": "Final status label (e.g., completed, blocked, parked).",
                        },
                        "links": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "description": "URLs to created items (Linear issues, Smartsheet rows, etc.)",
                            },
                            "description": "List of relevant links.",
                        },
                    },
                    "required": ["summary"],
                    "additionalProperties": True,
                },
            }
        )
        return defs

    def resolve_openai_tool_name(self, tool_name: str) -> str:
        """Map a sanitized OpenAI tool name back to an MCP fully-qualified name."""
        if tool_name in self._openai_name_to_fq:
            return self._openai_name_to_fq[tool_name]
        # Best effort: if already fq, return as-is
        if "." in tool_name:
            return tool_name
        raise KeyError(f"Unknown tool: {tool_name}")

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


def _extract_input_schema(tool_def: Tool):
    # Try several common attribute names and shapes
    for attr in ("input_schema", "inputSchema", "inputschema", "schema"):
        if hasattr(tool_def, attr):
            schema = getattr(tool_def, attr)
            if schema is None:
                return None
            # Pydantic-style objects
            if hasattr(schema, "model_dump"):
                return schema.model_dump()
            if hasattr(schema, "to_dict"):
                return schema.to_dict()
            if isinstance(schema, dict):
                return schema
    # Some MCP servers may not provide a schema
    return None
