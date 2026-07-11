"""Checker for set literals."""

import ast
from typing import List

from checkers._framework import Diagnostic, Severity, add_rule, make_diagnostic
from checkers._support import parse, node_position

RULE = add_rule(
    Severity.ERROR,
    "set literal or set operation",
    ["lists or dictionaries"],
)


def check_source(source: str, filename: str = "<string>") -> List[Diagnostic]:
    tree = parse(source)
    if tree is None:
        return []
    diagnostics = []
    for node in ast.walk(tree):
        is_set_literal = isinstance(node, ast.Set)
        is_set_constructor = (
            isinstance(node, ast.Call) and
            isinstance(node.func, ast.Name) and
            node.func.id == "set"
        )
        if is_set_literal or is_set_constructor:
            line, column = node_position(node)
            diagnostics.append(make_diagnostic(filename, line, column, RULE))
    return diagnostics
