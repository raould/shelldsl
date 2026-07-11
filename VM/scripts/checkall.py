#!/usr/bin/env python3
"""Run every registered source checker against each file argument."""

import importlib
import os
import pkgutil
import sys
from typing import Callable, Dict, List


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
VM_DIR = os.path.dirname(SCRIPT_DIR)
SRC_DIR = os.path.join(VM_DIR, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

import checkers
from checkers._framework import format_diagnostic
from checkers._support import (
    clear_inspection_context,
    prepare_inspection_context,
)


Diagnostic = Dict[str, object]
Checker = Callable[[str, str], List[Diagnostic]]

def discover_checkers() -> List[tuple]:
    """Discover every checker package (implements `check_source()`) below the checker parent directory."""
    discovered = []
    for module_info in pkgutil.iter_modules(checkers.__path__):
        if module_info.name.startswith("_"):
            continue
        module = importlib.import_module(
            "checkers.%s" % module_info.name
        )
        checker = getattr(module, "check_source", None)
        if checker is not None:
            discovered.append((module_info.name, checker))
    return discovered


CHECKERS: List[tuple] = discover_checkers()


def check_file(filename: str) -> List[Diagnostic]:
    """Apply all known checkers to one source file."""
    handle = open(filename, "r")
    try:
        source = handle.read()
    finally:
        handle.close()

    diagnostics: List[Diagnostic] = []
    context = prepare_inspection_context(source, filename)
    try:
        for checker_name, checker in CHECKERS:
            context_checker = getattr(
                importlib.import_module(checker.__module__),
                "check_context",
                None,
            )
            if context_checker is not None:
                checker_diagnostics = context_checker(context)
            else:
                checker_diagnostics = checker(source, filename)
            diagnostics.extend(checker_diagnostics)
    finally:
        clear_inspection_context()
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
