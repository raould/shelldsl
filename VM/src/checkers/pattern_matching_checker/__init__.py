"""Reject structural pattern matching."""
import ast
import tokenize
from typing import List
from checkers._framework import Diagnostic, Severity, add_rule, make_diagnostic
from checkers._support import parse, node_position, tokens
RULE = add_rule(Severity.ERROR, "structural pattern matching", ["if and elif statements"])
def check_source(source: str, filename: str = "<string>") -> List[Diagnostic]:
    tree = parse(source)
    if tree is not None and hasattr(ast, "Match"):
        return [make_diagnostic(filename, node_position(node)[0], node_position(node)[1], RULE) for node in ast.walk(tree) if isinstance(node, ast.Match)]
    return [make_diagnostic(filename, token.start[0], token.start[1] + 1, RULE) for token in tokens(source) if token.type == tokenize.NAME and token.string in ("match", "case")]
