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
    def test_expected_fail_directory_is_not_empty(self):
        self.assertTrue(
            _fixture_filenames(),
            "expected_fails must contain at least one Python fixture",
        )


def _fixture_filenames():
    return sorted(
        os.path.join(EXPECTED_FAILS_DIR, name)
        for name in os.listdir(EXPECTED_FAILS_DIR)
        if name.endswith(".py") and os.path.isfile(
            os.path.join(EXPECTED_FAILS_DIR, name)
        )
    )


def _make_fixture_test(filename):
    def test_fixture(self):
        diagnostics = checkall.check_file(filename)
        self.assertTrue(
            diagnostics,
            "static checking reported no diagnostics for %s" % filename,
        )

    return test_fixture


for _filename in _fixture_filenames():
    _test_name = "test_fixture_%s" % os.path.splitext(
        os.path.basename(_filename)
    )[0]
    setattr(
        ExpectedFailureFixtureTests,
        _test_name,
        _make_fixture_test(_filename),
    )


if __name__ == "__main__":
    unittest.main()
