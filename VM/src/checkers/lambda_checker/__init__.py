"""Reject lambda expressions."""
import ast
from typing import List
from checkers._framework import Diagnostic, Severity, add_rule, make_diagnostic
from checkers._support import parse, node_position
RULE = add_rule(Severity.ERROR, "lambda expression", ["named function"])
def check_source(source: str, filename: str = "<string>") -> List[Diagnostic]:
    tree = parse(source)
    if tree is None:
        return []
    return [make_diagnostic(filename, node_position(node)[0], node_position(node)[1], RULE) for node in ast.walk(tree) if isinstance(node, ast.Lambda)]
