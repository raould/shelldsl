"""Checker for prohibited print usage."""

import io
import tokenize
from typing import List

from checkers._framework import Diagnostic
from checkers._framework import Severity
from checkers._framework import add_rule
from checkers._framework import make_diagnostic


RULE = add_rule(
    Severity.ERROR,
    "print",
    ["prnt", "vm_sdk.write", "sys.stdout.write"],
)


def check_source(source: str, filename: str = "<string>") -> List[Diagnostic]:
    """Return diagnostics for Python 2 and Python 3 print syntax."""
    diagnostics = []
    reader = io.StringIO(source).readline
    try:
        for token in tokenize.generate_tokens(reader):
            if token.type == tokenize.NAME and token.string == "print":
                diagnostics.append(
                    make_diagnostic(
                        filename, token.start[0], token.start[1] + 1, RULE
                    )
                )
    except (tokenize.TokenError, IndentationError, SyntaxError):
        pass
    return diagnostics


check_print = check_source
