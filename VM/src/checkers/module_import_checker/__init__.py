"""Reject imports outside the small portable module allowlist."""
import ast
from typing import List
from checkers._framework import Diagnostic, Severity, add_rule, make_diagnostic
from checkers._support import parse, node_position
RULE = add_rule(Severity.ERROR, "unsupported module import", ["portable allowlisted modules"])
ALLOWLIST = set((
    "sys", "os", "string", "time", "math", "vm_sdk",
    "shlex", "shutil", "subprocess", "csv", "io", "json",
    "shelldsl", "core", "errors", "result",
))
def check_source(source: str, filename: str = "<string>") -> List[Diagnostic]:
    tree = parse(source)
    if tree is None:
        return []
    found = []
    for node in ast.walk(tree):
        names = []
        if isinstance(node, ast.Import):
            names = [alias.name.split(".")[0] for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            names = [node.module.split(".")[0]]
        if any(name not in ALLOWLIST for name in names):
            line, column = node_position(node)
            found.append(make_diagnostic(filename, line, column, RULE))
    return found
