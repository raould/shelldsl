"""Tests for dual-source PRNTLOG level gating."""

import os
import sys
import unittest
from io import StringIO


SRC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

import shelldsl_sdk  # noqa: E402


class PrntLogTests(unittest.TestCase):
    def setUp(self):
        self.old_environment = os.environ.get("PRNTLOGLEVEL")
        self.had_environment = "PRNTLOGLEVEL" in os.environ
        self.old_level = shelldsl_sdk.PRNTLOG_LEVEL
        shelldsl_sdk.set_prntlog_level(None)

    def tearDown(self):
        if self.had_environment:
            os.environ["PRNTLOGLEVEL"] = self.old_environment
        elif "PRNTLOGLEVEL" in os.environ:
            del os.environ["PRNTLOGLEVEL"]
        shelldsl_sdk.PRNTLOG_LEVEL = self.old_level

    def capture(self, level):
        output = StringIO()
        old_stderr = sys.stderr
        sys.stderr = output
        try:
            shelldsl_sdk.prntlog(level, "message")
        finally:
            sys.stderr = old_stderr
        return output.getvalue()

    def test_default_threshold_is_warn(self):
        self.assertEqual(self.capture(shelldsl_sdk.VERBOSE), "")
        self.assertIn("WARN", self.capture(shelldsl_sdk.WARN))
        self.assertIn("ERROR", self.capture(shelldsl_sdk.ERROR))

    def test_environment_verbose_enables_verbose_output(self):
        os.environ["PRNTLOGLEVEL"] = "VERBOSE"
        self.assertIn("VERBOSE", self.capture(shelldsl_sdk.VERBOSE))

    def test_environment_error_suppresses_warn(self):
        os.environ["PRNTLOGLEVEL"] = "ERROR"
        self.assertEqual(self.capture(shelldsl_sdk.WARN), "")
        self.assertIn("ERROR", self.capture(shelldsl_sdk.ERROR))

    def test_programmatic_verbose_wins_over_unset_environment(self):
        shelldsl_sdk.set_prntlog_level(shelldsl_sdk.VERBOSE)
        self.assertIn("VERBOSE", self.capture(shelldsl_sdk.VERBOSE))

    def test_louder_of_environment_and_programmatic_levels_wins(self):
        os.environ["PRNTLOGLEVEL"] = "ERROR"
        shelldsl_sdk.set_prntlog_level(shelldsl_sdk.VERBOSE)
        self.assertIn("VERBOSE", self.capture(shelldsl_sdk.VERBOSE))

    def test_level_names_are_accepted(self):
        os.environ["PRNTLOGLEVEL"] = "verbose"
        self.assertIn("VERBOSE", self.capture("VERBOSE"))


if __name__ == "__main__":
    unittest.main()