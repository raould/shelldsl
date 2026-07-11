"""Ensure every expected-failure fixture is rejected by static checking."""

import os
import sys
import unittest


VM_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCRIPT_DIR = os.path.join(VM_DIR, "scripts")
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import checkall  # noqa: E402


EXPECTED_FAILS_DIR = os.path.join(os.path.dirname(__file__), "expected_fails")


class ExpectedFailureFixtureTests(unittest.TestCase):
    def test_every_fixture_produces_static_diagnostics(self):
        filenames = sorted(
            os.path.join(EXPECTED_FAILS_DIR, name)
            for name in os.listdir(EXPECTED_FAILS_DIR)
            if name.endswith(".py") and os.path.isfile(
                os.path.join(EXPECTED_FAILS_DIR, name)
            )
        )
        self.assertTrue(
            filenames,
            "expected_fails must contain at least one Python fixture",
        )

        for filename in filenames:
            with self.subTest(filename=os.path.basename(filename)):
                diagnostics = checkall.check_file(filename)
                self.assertTrue(
                    diagnostics,
                    "static checking reported no diagnostics for %s" % filename,
                )


if __name__ == "__main__":
    unittest.main()
