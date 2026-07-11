"""Checker for set literals."""

import ast
from typing import List

from checkers._framework import Diagnostic, Severity, add_rule, make_diagnostic
from checkers._support import parse, node_position

RULE = add_rule(Severity.ERROR, "set literal or set operation", ["lists or dictionaries"])


def check_source(source: str, filename: str = "<string>") -> List[Diagnostic]:
    tree = parse(source)
    if tree is None:
        return []
    diagnostics = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Set):
            line, column = node_position(node)
            diagnostics.append(make_diagnostic(filename, line, column, RULE))
    return diagnostics
