"""Reject dictionary unpacking syntax."""

import ast
from typing import List

from checkers._framework import Diagnostic, Severity, add_rule, make_diagnostic
from checkers._support import node_position, parse

RULE = add_rule(
    Severity.ERROR,
    "dictionary unpacking",
    ["explicit dictionary assignments and arguments"],
)


def check_source(source: str, filename: str = "<string>") -> List[Diagnostic]:
    tree = parse(source)
    if tree is None:
        return []
    diagnostics = []
    for node in ast.walk(tree):
        unpacking = isinstance(node, ast.Dict) and any(
            key is None for key in node.keys
        )
        unpacking = unpacking or (
            isinstance(node, ast.Call) and any(
                keyword.arg is None for keyword in node.keywords
            )
        )
        if unpacking:
            line, column = node_position(node)
            diagnostics.append(make_diagnostic(filename, line, column, RULE))
    return diagnostics
