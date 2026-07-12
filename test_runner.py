#!/usr/bin/env python3
"""Run the shelldsl host-library tests."""

import os
import sys
import unittest


ROOT = os.path.dirname(os.path.abspath(__file__))
TEST_DIR = os.path.join(ROOT, "test")
SRC_DIR = os.path.join(ROOT, "src")

if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.discover(
        start_dir=TEST_DIR,
        pattern="test_*.py",
        top_level_dir=TEST_DIR,
    )
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
