"""Reject Python 3-style explicit object base classes."""
import tokenize
from typing import List
from checkers._framework import Diagnostic, Severity, add_rule, make_diagnostic
from checkers._support import tokens
RULE = add_rule(Severity.ERROR, "new-style class declaration", ["old-style class declaration"])
def check_source(source: str, filename: str = "<string>") -> List[Diagnostic]:
    found = []
    stream = tokens(source)
    for index in range(len(stream) - 4):
        if (stream[index].type == tokenize.NAME and stream[index].string == "class" and stream[index + 2].string == "(" and stream[index + 3].type == tokenize.NAME and stream[index + 3].string == "object"):
            found.append(make_diagnostic(filename, stream[index].start[0], stream[index].start[1] + 1, RULE))
    return found
