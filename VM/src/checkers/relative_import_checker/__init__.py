"""Reject ambiguous implicit-relative import forms."""
import ast
from typing import List
from checkers._framework import Diagnostic, Severity, add_rule, make_diagnostic
from checkers._support import parse, node_position
RULE = add_rule(Severity.ERROR, "implicit relative import", ["explicit absolute import"])
def check_source(source: str, filename: str = "<string>") -> List[Diagnostic]:
    tree = parse(source)
    if tree is None:
        return []
    # Python 3 cannot determine whether an absolute import was intended to
    # be relative without package context. Do not guess and create a false
    # positive; explicit relative imports are represented by level > 0.
    return [make_diagnostic(filename, node_position(node)[0], node_position(node)[1], RULE) for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.level > 0 and node.module is None]
