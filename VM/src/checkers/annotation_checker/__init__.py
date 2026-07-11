"""Checker for Python 3 annotations."""

import ast
from typing import List

from checkers._framework import Diagnostic, Severity, add_rule, make_diagnostic
from checkers._support import parse, node_position

RULE = add_rule(Severity.ERROR, "function or variable annotations", ["type comments"])


def check_source(source: str, filename: str = "<string>") -> List[Diagnostic]:
    tree = parse(source)
    if tree is None:
        return []
    diagnostics = []
    for node in ast.walk(tree):
        annotated = isinstance(node, ast.AnnAssign)
        annotated = annotated or isinstance(node, ast.arg) and node.annotation is not None
        annotated = annotated or isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and (
            node.returns is not None or any(argument.annotation is not None for argument in node.args.args)
        )
        if annotated:
            line, column = node_position(node)
            diagnostics.append(make_diagnostic(filename, line, column, RULE))
    return diagnostics
