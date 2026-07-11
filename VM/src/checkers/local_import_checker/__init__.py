"""Reject imports nested in functions or classes."""
import ast
from typing import List
from checkers._framework import Diagnostic, Severity, add_rule, make_diagnostic
from checkers._support import parse, node_position
RULE = add_rule(Severity.ERROR, "import inside a function", ["module-level imports"])
def check_source(source: str, filename: str = "<string>") -> List[Diagnostic]:
    tree = parse(source)
    if tree is None:
        return []
    found = []
    def visit(node, nested):
        for child in ast.iter_child_nodes(node):
            if nested and isinstance(child, (ast.Import, ast.ImportFrom)):
                line, column = node_position(child)
                found.append(make_diagnostic(filename, line, column, RULE))
            visit(child, nested or isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)))
    visit(tree, False)
    return found
