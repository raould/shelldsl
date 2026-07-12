"""Reject nested function definitions."""
import ast
from typing import List
from checkers._framework import Diagnostic, Severity, add_rule, make_diagnostic
from checkers._support import parse, node_position
RULE = add_rule(Severity.ERROR, "nested function definition", ["top-level function and explicit state"])
def check_source(source: str, filename: str = "<string>") -> List[Diagnostic]:
    tree = parse(source)
    if tree is None:
        return []
    found = []
    def visit(node, inside_function):
        for child in ast.iter_child_nodes(node):
            is_function = isinstance(
                child, (ast.FunctionDef, ast.AsyncFunctionDef)
            )
            if is_function and inside_function:
                line, column = node_position(child)
                found.append(make_diagnostic(filename, line, column, RULE))
            if isinstance(child, ast.ClassDef):
                visit(child, False)
            else:
                visit(child, inside_function or is_function)
    visit(tree, False)
    return found
