#!/usr/bin/env python3
"""Compatibility entry point for checking application source files."""

import sys

from checkall import main


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
