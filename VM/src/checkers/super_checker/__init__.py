"""Reject the Python 3 super() convenience call."""

import ast
from typing import List

from checkers._framework import Diagnostic, Severity, add_rule, make_diagnostic
from checkers._support import node_position, parse

RULE = add_rule(
    Severity.ERROR,
    "super() call",
    ["explicit base-class method call"],
)


def check_source(source: str, filename: str = "<string>") -> List[Diagnostic]:
    tree = parse(source)
    if tree is None:
        return []
    diagnostics = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and
                node.func.id == "super"):
            line, column = node_position(node)
            diagnostics.append(make_diagnostic(filename, line, column, RULE))
    return diagnostics
