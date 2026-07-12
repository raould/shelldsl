"""Checker for exception binding with `as`."""

import tokenize
from typing import List

from checkers._framework import Diagnostic, Severity, add_rule, make_diagnostic
from checkers._support import tokens

RULE = add_rule(
    Severity.ERROR,
    "exception binding with as",
    ["vm_sdk.exception_value", "sys.exc_info()"],
)


def check_source(source: str, filename: str = "<string>") -> List[Diagnostic]:
    diagnostics = []
    token_list = tokens(source)
    in_except = False
    for index in range(len(token_list) - 1):
        current = token_list[index]
        following = token_list[index + 1]
        if current.type == tokenize.NEWLINE:
            in_except = False
        elif current.type == tokenize.NAME and current.string == "except":
            in_except = True
        elif (in_except and current.type == tokenize.NAME and current.string == "as" and
                following.type == tokenize.NAME):
            diagnostics.append(make_diagnostic(filename, current.start[0], current.start[1] + 1, RULE))
    return diagnostics
