#!/usr/bin/env python3
"""Run every registered source checker against each file argument."""

import os
import sys
from typing import Callable, Dict, List


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.dirname(SCRIPT_DIR)
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from portable_check import check_print
from portable_check import format_diagnostic


Diagnostic = Dict[str, object]
Checker = Callable[[str, str], List[Diagnostic]]

# Add future checkers here. Each checker receives source text and a filename,
# and returns structured diagnostics without executing the inspected source.
CHECKERS: List[tuple] = [
    ("print", check_print),
]


def check_file(filename: str) -> List[Diagnostic]:
    """Apply all known checkers to one source file."""
    handle = open(filename, "r")
    try:
        source = handle.read()
    finally:
        handle.close()

    diagnostics: List[Diagnostic] = []
    for checker_name, checker in CHECKERS:
        checker_diagnostics = checker(source, filename)
        diagnostics.extend(checker_diagnostics)
    return diagnostics


def main(arguments: List[str]) -> int:
    """Check every file argument and return a process status."""
    if len(arguments) == 0:
        sys.stderr.write("usage: checkall.py SOURCE...\n")
        return 2

    found_error = 0
    for filename in arguments:
        if not os.path.isfile(filename):
            sys.stderr.write("error: file not found: %s\n" % filename)
            found_error = 1
            continue

        try:
            diagnostics = check_file(filename)
        except (IOError, OSError) as error:
            sys.stderr.write("error: cannot read %s: %s\n" % (filename, error))
            found_error = 1
            continue

        for diagnostic in diagnostics:
            sys.stdout.write(format_diagnostic(diagnostic) + "\n")
        if len(diagnostics) != 0:
            found_error = 1

    return found_error


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
