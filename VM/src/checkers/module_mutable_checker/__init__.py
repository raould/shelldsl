"""Reject mutable values assigned at module scope."""
import ast
from typing import List
from checkers._framework import Diagnostic, Severity, add_rule, make_diagnostic
from checkers._support import parse, node_position
RULE = add_rule(Severity.ERROR, "module-level mutable state", ["function-created state"])
def check_source(source: str, filename: str = "<string>") -> List[Diagnostic]:
    tree = parse(source)
    if tree is None:
        return []
    found = []
    for node in tree.body:
        value = node.value if isinstance(node, ast.Assign) else node.value if isinstance(node, ast.AnnAssign) else None
        if isinstance(value, (ast.List, ast.Dict, ast.Set)):
            line, column = node_position(node)
            found.append(make_diagnostic(filename, line, column, RULE))
    return found
