"""Reject hidden shared-state declarations."""
import ast
from typing import List
from checkers._framework import Diagnostic, Severity, add_rule, make_diagnostic
from checkers._support import parse, node_position
RULE = add_rule(Severity.ERROR, "global or nonlocal declaration", ["explicit state argument"])
def check_source(source: str, filename: str = "<string>") -> List[Diagnostic]:
    tree = parse(source)
    if tree is None:
        return []
    found = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Global, ast.Nonlocal)):
            line, column = node_position(node)
            found.append(make_diagnostic(filename, line, column, RULE))
    return found
