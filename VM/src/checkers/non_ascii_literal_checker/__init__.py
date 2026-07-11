"""Reject non-ASCII string literals under the ASCII diagnostic policy."""
import tokenize
from typing import List
from checkers._framework import Diagnostic, Severity, add_rule, make_diagnostic
from checkers._support import tokens
RULE = add_rule(Severity.ERROR, "non-ASCII diagnostic literal", ["ASCII literal or explicit encoding"])
def check_source(source: str, filename: str = "<string>") -> List[Diagnostic]:
    found = []
    for token in tokens(source):
        if token.type == tokenize.STRING and any(ord(char) > 127 for char in token.string):
            found.append(make_diagnostic(filename, token.start[0], token.start[1] + 1, RULE))
    return found
