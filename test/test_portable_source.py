"""Run the VM source checker against every shelldsl source file."""

import os
import subprocess
import sys
import unittest


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC_DIR = os.path.join(ROOT, "src")
CHECKER = os.path.join(ROOT, "VM", "scripts", "checkapp.py")


class PortableSourceTests(unittest.TestCase):
    def test_checker_runs_for_each_source_file(self):
        filenames = []
        for directory, unused_names, names in os.walk(SRC_DIR):
            for name in names:
                if name.endswith(".py"):
                    filenames.append(os.path.join(directory, name))
        filenames.sort()
        self.assertTrue(filenames, "src must contain Python files")

        for filename in filenames:
            with self.subTest(filename=os.path.relpath(filename, ROOT)):
                process = subprocess.Popen(
                    [sys.executable, CHECKER, filename],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True,
                )
                stdout, stderr = process.communicate()
                self.assertNotEqual(
                    process.returncode,
                    2,
                    "checker could not run for %s: %s" % (filename, stderr),
                )
                self.assertNotIn("Traceback", stderr + stdout)


if __name__ == "__main__":
    unittest.main()
