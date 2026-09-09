"""
Small, safe raster calculator.

Only supports named bands (A, B), numeric literals, and + - * / ( ), parsed
with Python's `ast` module and validated against a strict whitelist of node
types -- this deliberately cannot execute arbitrary code, unlike a bare
`eval()`.
"""
from __future__ import annotations

import ast
import operator

import numpy as np

from app.utils.errors import ProcessingError

_ALLOWED_BINOPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}
_ALLOWED_UNARY = {ast.UAdd: operator.pos, ast.USub: operator.neg}


def _eval_node(node: ast.AST, bands: dict[str, np.ndarray]):
    if isinstance(node, ast.Expression):
        return _eval_node(node.body, bands)
    if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_BINOPS:
        return _ALLOWED_BINOPS[type(node.op)](_eval_node(node.left, bands), _eval_node(node.right, bands))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_UNARY:
        return _ALLOWED_UNARY[type(node.op)](_eval_node(node.operand, bands))
    if isinstance(node, ast.Name):
        if node.id not in bands:
            raise ProcessingError(f"Unknown band '{node.id}' in expression.", hint="Use A and/or B.")
        return bands[node.id]
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    raise ProcessingError(
        "That expression isn't supported.",
        hint="Only band names (A, B), numbers, and + - * / ( ) are allowed.",
    )


def evaluate(expression: str, a: np.ndarray, b: np.ndarray | None = None) -> np.ndarray:
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise ProcessingError("That expression couldn't be parsed.") from exc
    bands = {"A": a}
    if b is not None:
        bands["B"] = b
    with np.errstate(divide="ignore", invalid="ignore"):
        result = _eval_node(tree, bands)
    return np.asarray(result, dtype="float32")
