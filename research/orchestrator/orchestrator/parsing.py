from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from typing import Dict, List


TOOL_CALL_PREFIX = "TOOL_CALL:"


@dataclass(slots=True)
class ToolCall:
    name: str
    arguments: Dict[str, object]


def extract_tool_calls(text: str) -> List[ToolCall]:
    calls: List[ToolCall] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line.startswith(TOOL_CALL_PREFIX):
            continue
        payload = line[len(TOOL_CALL_PREFIX) :].strip()
        if not payload:
            continue
        call = _parse_call(payload)
        calls.append(call)
    return calls


def strip_tool_call_lines(text: str) -> str:
    lines = [
        line
        for line in text.splitlines()
        if not line.strip().startswith(TOOL_CALL_PREFIX)
    ]
    return "\n".join(lines).strip()


def _parse_call(payload: str) -> ToolCall:
    try:
        tree = ast.parse(payload, mode="eval")
    except SyntaxError as exc:
        raise ValueError(f"Invalid TOOL_CALL syntax: {payload}") from exc

    if not isinstance(tree.body, ast.Call):
        raise ValueError(f"Invalid TOOL_CALL expression: {payload}")

    func_expr = tree.body.func
    name = _resolve_func_name(func_expr)

    if tree.body.args:
        raise ValueError(
            f"TOOL_CALL must use keyword arguments only: {payload}"
        )

    arguments: Dict[str, object] = {}
    for keyword in tree.body.keywords:
        if keyword.arg is None:
            raise ValueError(f"Invalid keyword argument in {payload}")
        arguments[keyword.arg] = ast.literal_eval(keyword.value)

    return ToolCall(name=name, arguments=arguments)


def _resolve_func_name(func_expr: ast.AST) -> str:
    if isinstance(func_expr, ast.Name):
        return func_expr.id
    if isinstance(func_expr, ast.Attribute):
        return f"{_resolve_func_name(func_expr.value)}.{func_expr.attr}"
    raise ValueError("Unsupported tool name expression")
