"""Checker for comprehensions and generator expressions."""

import ast
from typing import List

from checkers._framework import Diagnostic, Severity, add_rule, make_diagnostic
from checkers._support import parse, node_position

RULE = add_rule(Severity.ERROR, "comprehension or generator expression", ["explicit loops"])


def check_source(source: str, filename: str = "<string>") -> List[Diagnostic]:
    tree = parse(source)
    if tree is None:
        return []
    kinds = (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)
    diagnostics = []
    for node in ast.walk(tree):
        if isinstance(node, kinds):
            line, column = node_position(node)
            diagnostics.append(make_diagnostic(filename, line, column, RULE))
    return diagnostics
