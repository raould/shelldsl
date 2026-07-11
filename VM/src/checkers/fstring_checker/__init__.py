"""Checker for Python 3 f-string interpolation."""

import io
import tokenize
from typing import List

from checkers._framework import Diagnostic
from checkers._framework import Severity
from checkers._framework import add_rule
from checkers._framework import make_diagnostic


RULE = add_rule(Severity.ERROR, "f-string", ["%-formatting"])


def _is_f_string(value: str) -> bool:
    """Return whether a token is a string with an f-string prefix."""
    quote = value.find("\"")
    single_quote = value.find("'")
    if quote == -1 or (single_quote != -1 and single_quote < quote):
        quote = single_quote
    if quote == -1:
        return False
    prefix = value[:quote].lower()
    return "f" in prefix


def check_source(source: str, filename: str = "<string>") -> List[Diagnostic]:
    """Return a diagnostic for every f-string token in source text."""
    diagnostics = []
    reader = io.StringIO(source).readline
    f_string_start = getattr(tokenize, "FSTRING_START", -1)
    try:
        for token in tokenize.generate_tokens(reader):
            is_f_string = (
                token.type == f_string_start
                or (
                    token.type == tokenize.STRING
                    and _is_f_string(token.string)
                )
            )
            if is_f_string:
                diagnostics.append(
                    make_diagnostic(
                        filename, token.start[0], token.start[1] + 1, RULE
                    )
                )
    except (tokenize.TokenError, IndentationError, SyntaxError):
        pass
    return diagnostics


check_fstring = check_source
