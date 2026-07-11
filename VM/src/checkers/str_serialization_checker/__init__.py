"""Reject str(value) at obvious output and command boundaries."""
import ast
from typing import List
from checkers._framework import Diagnostic, Severity, add_rule, make_diagnostic
from checkers._support import parse, node_position
RULE = add_rule(Severity.ERROR, "arbitrary str() serialization", ["explicit serialization format"])
def check_source(source: str, filename: str = "<string>") -> List[Diagnostic]:
    tree = parse(source)
    if tree is None:
        return []
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in ("write", "run", "system"):
            if any(isinstance(child, ast.Call) and isinstance(child.func, ast.Name) and child.func.id == "str" for child in ast.walk(node)):
                line, column = node_position(node)
                found.append(make_diagnostic(filename, line, column, RULE))
    return found
