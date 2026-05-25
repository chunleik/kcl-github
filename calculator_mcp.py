#!/usr/bin/env python3
"""A high-performance calculator MCP server over stdio (JSON-RPC 2.0)."""

from __future__ import annotations

import ast
import json
import math
import sys
from dataclasses import dataclass
from typing import Any, Callable

JSON = dict[str, Any]


class CalculatorError(Exception):
    pass


@dataclass(frozen=True)
class Operator:
    fn: Callable[[float, float], float]
    arity: int = 2


class SafeEvaluator(ast.NodeVisitor):
    """Safely evaluate arithmetic expressions with selected math functions."""

    BIN_OPS: dict[type[ast.AST], Operator] = {
        ast.Add: Operator(lambda a, b: a + b),
        ast.Sub: Operator(lambda a, b: a - b),
        ast.Mult: Operator(lambda a, b: a * b),
        ast.Div: Operator(lambda a, b: a / b),
        ast.FloorDiv: Operator(lambda a, b: a // b),
        ast.Mod: Operator(lambda a, b: a % b),
        ast.Pow: Operator(lambda a, b: a**b),
    }
    UNARY_OPS: dict[type[ast.AST], Callable[[float], float]] = {
        ast.UAdd: lambda a: +a,
        ast.USub: lambda a: -a,
    }

    FUNCS: dict[str, Callable[..., float]] = {
        "sqrt": math.sqrt,
        "sin": math.sin,
        "cos": math.cos,
        "tan": math.tan,
        "log": math.log,
        "log10": math.log10,
        "exp": math.exp,
        "abs": abs,
        "round": round,
        "ceil": math.ceil,
        "floor": math.floor,
        "factorial": math.factorial,
    }

    CONSTS: dict[str, float] = {"pi": math.pi, "e": math.e}

    def __init__(self, ans: float | None = None) -> None:
        self.ans = ans

    def evaluate(self, expression: str) -> float:
        try:
            node = ast.parse(expression, mode="eval")
        except SyntaxError as exc:
            raise CalculatorError(f"表达式语法错误: {exc.msg}") from exc
        result = self.visit(node.body)
        if isinstance(result, complex):
            raise CalculatorError("不支持复数运算")
        return float(result)

    def visit_BinOp(self, node: ast.BinOp) -> float:
        op = self.BIN_OPS.get(type(node.op))
        if not op:
            raise CalculatorError("不支持的二元操作符")
        left = self.visit(node.left)
        right = self.visit(node.right)
        try:
            return op.fn(left, right)
        except ZeroDivisionError as exc:
            raise CalculatorError("除数不能为0") from exc
        except ValueError as exc:
            raise CalculatorError(str(exc)) from exc

    def visit_UnaryOp(self, node: ast.UnaryOp) -> float:
        fn = self.UNARY_OPS.get(type(node.op))
        if not fn:
            raise CalculatorError("不支持的一元操作符")
        return fn(self.visit(node.operand))

    def visit_Call(self, node: ast.Call) -> float:
        if not isinstance(node.func, ast.Name):
            raise CalculatorError("仅允许调用白名单函数")
        name = node.func.id
        func = self.FUNCS.get(name)
        if func is None:
            raise CalculatorError(f"不支持函数: {name}")
        args = [self.visit(arg) for arg in node.args]
        if node.keywords:
            raise CalculatorError("不支持关键字参数")
        try:
            return float(func(*args))
        except (ValueError, TypeError, OverflowError) as exc:
            raise CalculatorError(str(exc)) from exc

    def visit_Name(self, node: ast.Name) -> float:
        if node.id == "ans":
            if self.ans is None:
                raise CalculatorError("ans 尚未定义")
            return self.ans
        if node.id in self.CONSTS:
            return self.CONSTS[node.id]
        raise CalculatorError(f"未知变量: {node.id}")

    def visit_Constant(self, node: ast.Constant) -> float:
        if isinstance(node.value, (int, float)):
            return float(node.value)
        raise CalculatorError("仅允许数字常量")

    def generic_visit(self, node: ast.AST) -> Any:
        raise CalculatorError(f"不支持的语法节点: {type(node).__name__}")


class MCPServer:
    PROTOCOL_VERSION = "2025-11-25"

    def __init__(self) -> None:
        self.last_result: float | None = None

    def _ok(self, request_id: Any, result: Any) -> str:
        return json.dumps({"jsonrpc": "2.0", "id": request_id, "result": result}, ensure_ascii=False)

    def _err(self, request_id: Any, code: int, message: str) -> str:
        return json.dumps(
            {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}},
            ensure_ascii=False,
        )

    def handle(self, raw: str) -> str | None:
        try:
            req = json.loads(raw)
        except json.JSONDecodeError:
            return self._err(None, -32700, "Parse error")

        request_id = req.get("id")
        method = req.get("method")
        params = req.get("params", {})

        try:
            if method == "initialize":
                return self._ok(
                    request_id,
                    {
                        "protocolVersion": self.PROTOCOL_VERSION,
                        "serverInfo": {"name": "calculator-mcp", "version": "1.0.0"},
                        "capabilities": {"tools": {}},
                    },
                )

            if method == "tools/list":
                return self._ok(
                    request_id,
                    {
                        "tools": [
                            {
                                "name": "calculate",
                                "description": "计算数学表达式，支持 + - * / // % **、括号、ans、pi、e 和常见数学函数",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "expression": {"type": "string", "description": "要计算的表达式"}
                                    },
                                    "required": ["expression"],
                                },
                            }
                        ]
                    },
                )

            if method == "tools/call":
                if params.get("name") != "calculate":
                    return self._err(request_id, -32602, "Unknown tool")
                expression = (params.get("arguments") or {}).get("expression")
                if not isinstance(expression, str) or not expression.strip():
                    return self._err(request_id, -32602, "expression must be non-empty string")
                evaluator = SafeEvaluator(ans=self.last_result)
                value = evaluator.evaluate(expression)
                self.last_result = value
                return self._ok(
                    request_id,
                    {
                        "content": [
                            {
                                "type": "text",
                                "text": f"{value}",
                            }
                        ]
                    },
                )

            if method == "notifications/initialized":
                return None

            return self._err(request_id, -32601, f"Method not found: {method}")
        except CalculatorError as exc:
            return self._err(request_id, -32000, str(exc))
        except Exception as exc:  # noqa: BLE001
            return self._err(request_id, -32099, f"Internal error: {exc}")

    def serve(self) -> None:
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            response = self.handle(line)
            if response is not None:
                sys.stdout.write(response + "\n")
                sys.stdout.flush()


def main() -> None:
    MCPServer().serve()


if __name__ == "__main__":
    main()
