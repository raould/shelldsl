"""Reject assignment expressions."""
import tokenize
from typing import List
from checkers._framework import Diagnostic, Severity, add_rule, make_diagnostic
from checkers._support import tokens
RULE = add_rule(Severity.ERROR, "assignment expression", ["separate assignment statement"])
def check_source(source: str, filename: str = "<string>") -> List[Diagnostic]:
    return [make_diagnostic(filename, token.start[0], token.start[1] + 1, RULE) for token in tokens(source) if token.string == ":="]
