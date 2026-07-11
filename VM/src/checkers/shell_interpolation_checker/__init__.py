"""Reject obvious interpolated shell command construction."""
import ast
from typing import List
from checkers._framework import Diagnostic, Severity, add_rule, make_diagnostic
from checkers._support import parse, node_position
RULE = add_rule(Severity.ERROR, "unsafe shell interpolation", ["argument-list command boundary"])
def check_source(source: str, filename: str = "<string>") -> List[Diagnostic]:
    tree = parse(source)
    if tree is None:
        return []
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        shell_call = (isinstance(node.func, ast.Name) and
                      node.func.id in ("system", "popen"))
        shell_call = shell_call or (
            isinstance(node.func, ast.Attribute) and
            node.func.attr in ("system", "popen")
        )
        if shell_call:
            if any(isinstance(arg, (ast.BinOp, ast.JoinedStr, ast.Call)) for arg in node.args):
                line, column = node_position(node)
                found.append(make_diagnostic(filename, line, column, RULE))
    return found
