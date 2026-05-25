#!/usr/bin/env python3
"""A calculator MCP server — supports both stdio and SSE transports."""

from __future__ import annotations

import ast
import math
import sys
from typing import Any

from mcp.server.fastmcp import FastMCP


class CalculatorError(Exception):
    pass


class SafeEvaluator(ast.NodeVisitor):
    """Safely evaluate arithmetic expressions with selected math functions."""

    BIN_OPS: dict[type[ast.AST], Any] = {
        ast.Add: lambda a, b: a + b,
        ast.Sub: lambda a, b: a - b,
        ast.Mult: lambda a, b: a * b,
        ast.Div: lambda a, b: a / b,
        ast.FloorDiv: lambda a, b: a // b,
        ast.Mod: lambda a, b: a % b,
        ast.Pow: lambda a, b: a**b,
    }
    UNARY_OPS: dict[type[ast.AST], Any] = {
        ast.UAdd: lambda a: +a,
        ast.USub: lambda a: -a,
    }

    FUNCS: dict[str, Any] = {
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

    def __init__(self) -> None:
        self._ans: float | None = None

    @property
    def ans(self) -> float | None:
        return self._ans

    @ans.setter
    def ans(self, value: float) -> None:
        self._ans = value

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
            return op(left, right)
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
            if self._ans is None:
                raise CalculatorError("ans 尚未定义")
            return self._ans
        if node.id in self.CONSTS:
            return self.CONSTS[node.id]
        raise CalculatorError(f"未知变量: {node.id}")

    def visit_Constant(self, node: ast.Constant) -> float:
        if isinstance(node.value, (int, float)):
            return float(node.value)
        raise CalculatorError("仅允许数字常量")

    def generic_visit(self, node: ast.AST) -> Any:
        raise CalculatorError(f"不支持的语法节点: {type(node).__name__}")


mcp = FastMCP("calculator-mcp", host="0.0.0.0", port=8000)

_evaluator = SafeEvaluator()


@mcp.tool()
def calculate(expression: str) -> str:
    """计算数学表达式。

    支持运算符: + - * / // % **
    支持函数: sqrt sin cos tan log log10 exp abs round ceil floor factorial
    支持常量: pi e
    支持上次结果: ans

    Args:
        expression: 要计算的数学表达式
    """
    value = _evaluator.evaluate(expression)
    _evaluator.ans = value
    return str(value)


def main() -> None:
    transport = "stdio"
    if len(sys.argv) > 1:
        transport = sys.argv[1]

    if transport == "sse":
        print(f"SSE endpoint: http://0.0.0.0:8000/sse")
        print(f"Messages endpoint: http://0.0.0.0:8000/messages/")

    try:
        mcp.run(transport=transport)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
