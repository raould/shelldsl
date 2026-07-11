"""Reject Python 2 long integer literal suffixes."""
import tokenize
from typing import List
from checkers._framework import Diagnostic, Severity, add_rule, make_diagnostic
from checkers._support import tokens
RULE = add_rule(Severity.ERROR, "Python 2 long literal suffix", ["ordinary integer literals"])
def check_source(source: str, filename: str = "<string>") -> List[Diagnostic]:
    found = []
    stream = tokens(source)
    for index in range(len(stream) - 1):
        number = stream[index]
        suffix = stream[index + 1]
        if (number.type == tokenize.NUMBER and suffix.type == tokenize.NAME and
                suffix.string in ("l", "L") and
                suffix.start[0] == number.end[0] and
                suffix.start[1] == number.end[1]):
            found.append(make_diagnostic(filename, number.start[0], number.start[1] + 1, RULE))
    return found
