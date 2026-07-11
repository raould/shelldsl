#!/usr/bin/env python3
"""Compatibility facade for the portable source checker API."""

import os
import sys
from typing import List

from checkers._framework import Diagnostic
from checkers._framework import RULES
from checkers._framework import RuleRegistrationError
from checkers._framework import Rule
from checkers._framework import Severity
from checkers._framework import add_rule
from checkers._framework import format_diagnostic
from checkers._framework import make_diagnostic
from checkers.print_checker import RULE as PRINT_RULE
from checkers.print_checker import check_source as check_print


def check_file(filename: str) -> List[Diagnostic]:
    """Read and check one source file without executing it."""
    handle = open(filename, "r")
    try:
        source = handle.read()
    finally:
        handle.close()
    return check_print(source, filename)


def source_is_portable(source: str, filename: str = "<string>") -> bool:
    """Return whether source has no error-severity print diagnostics."""
    diagnostics = check_print(source, filename)
    for diagnostic in diagnostics:
        if diagnostic["severity"] == Severity.ERROR:
            return False
    return True


def main(arguments: List[str]) -> int:
    """Check files named in arguments and return a process status."""
    if len(arguments) == 0:
        sys.stderr.write("usage: portable_check.py SOURCE...\n")
        return 2

    found_error = 0
    index = 0
    while index < len(arguments):
        filename = arguments[index]
        if not os.path.isfile(filename):
            sys.stderr.write("error: file not found: %s\n" % filename)
            found_error = 1
            index = index + 1
            continue

        diagnostics = check_file(filename)
        for diagnostic in diagnostics:
            sys.stdout.write(format_diagnostic(diagnostic) + "\n")
        if len(diagnostics) != 0:
            found_error = 1
        index = index + 1

    return found_error


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
