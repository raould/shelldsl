"""Reject positional-only function arguments."""

import ast
from typing import List

from checkers._framework import Diagnostic, Severity, add_rule, make_diagnostic
from checkers._support import node_position, parse

RULE = add_rule(
    Severity.ERROR,
    "positional-only arguments",
    ["explicit positional arguments"],
)


def check_source(source: str, filename: str = "<string>") -> List[Diagnostic]:
    tree = parse(source)
    if tree is None:
        return []
    diagnostics = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if getattr(node.args, "posonlyargs", []):
            line, column = node_position(node)
            diagnostics.append(make_diagnostic(filename, line, column, RULE))
    return diagnostics
