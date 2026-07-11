"""Small Python 2.0-compatible SDK shims for portable VM programs."""

import sys


def prnt(*values):
    """Write values separated by spaces and terminated by a newline."""
    index = 0
    while index < len(values):
        if index != 0:
            sys.stdout.write(" ")
        sys.stdout.write("%s" % values[index])
        index = index + 1
    sys.stdout.write("\n")


def write(value):
    """Write one value without adding a newline."""
    sys.stdout.write("%s" % value)


def int_div(left, right):
    """Return Python-style floor division without using `//` syntax."""
    return divmod(left, right)[0]


def exception_value():
    """Return the active exception value inside an except block."""
    return sys.exc_info()[1]
