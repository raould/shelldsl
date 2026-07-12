"""Tests for Docker runtime command construction."""

import os
import sys
import unittest


SCRIPT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import run_docker  # noqa: E402


class DockerRunnerTests(unittest.TestCase):
    def options(self, **values):
        defaults = {
            "image": "python:2.7",
            "project": os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "workdir": "/workspace",
            "read_only": True,
            "network_none": True,
            "name": None,
            "command": ["python", "-m", "unittest"],
        }
        defaults.update(values)
        return type("Options", (object,), defaults)()

    def test_builds_read_only_network_disabled_mount(self):
        command = run_docker.docker_arguments(self.options())
        self.assertEqual(command[0:3], ["docker", "run", "--rm"])
        self.assertIn("--network", command)
        self.assertIn("none", command)
        self.assertIn("--volume", command)
        mounts = [value for value in command if value.endswith(":/workspace:ro")]
        self.assertEqual(len(mounts), 1)
        self.assertEqual(command[-3:], ["python", "-m", "unittest"])

    def test_preserves_command_arguments_without_shell(self):
        command = run_docker.docker_arguments(
            self.options(
                read_only=False,
                network_none=False,
                command=["python", "script.py", "argument with spaces"],
            )
        )
        self.assertEqual(command[-3:], [
            "python", "script.py", "argument with spaces"
        ])
        self.assertNotIn("bash", command)

    def test_strips_argument_separator_before_container_command(self):
        command = run_docker.docker_arguments(
            self.options(command=["--", "python", "script.py"])
        )
        self.assertEqual(command[-2:], ["python", "script.py"])

    def test_requires_a_container_command(self):
        with self.assertRaises(ValueError):
            run_docker.docker_arguments(self.options(command=[]))

    def test_discovers_vm_dockerfiles(self):
        files = run_docker.dockerfiles()
        self.assertTrue(files)
        for filename in files:
            self.assertTrue(os.path.basename(filename).startswith("Dockerfile.py"))

    def test_generates_stable_image_name(self):
        self.assertEqual(
            run_docker.image_name("/tmp/Dockerfile.py_2_7"),
            "shelldsl-py-2-7",
        )

    def test_build_arguments_use_repository_as_context(self):
        command = run_docker.build_arguments(
            "/tmp/Dockerfile.py_2_7", "shelldsl-py-2-7"
        )
        self.assertEqual(command[:2], ["docker", "build"])
        self.assertEqual(command[-1], run_docker.repository_root())

    def test_project_defaults_to_current_directory(self):
        original_getcwd = run_docker.os.getcwd
        original_isdir = run_docker.os.path.isdir
        run_docker.os.getcwd = lambda: "/tmp/target-project"
        run_docker.os.path.isdir = lambda path: path == "/tmp/target-project"
        try:
            command = run_docker.docker_arguments(
                self.options(project=None)
            )
        finally:
            run_docker.os.getcwd = original_getcwd
            run_docker.os.path.isdir = original_isdir
        self.assertIn(
            "/tmp/target-project:/workspace:ro",
            command,
        )

    def test_parser_supports_rebuild(self):
        options = run_docker.build_parser().parse_args(
            ["--all", "--rebuild", "--", "python", "--version"]
        )
        self.assertTrue(options.all)
        self.assertTrue(options.rebuild)

    def test_image_exists_uses_docker_image_inspect(self):
        original_call = run_docker.subprocess.call
        calls = []

        def fake_call(command, **unused_options):
            calls.append(command)
            return 0

        run_docker.subprocess.call = fake_call
        try:
            self.assertTrue(run_docker.image_exists("shelldsl-py-3-14"))
        finally:
            run_docker.subprocess.call = original_call
        self.assertEqual(
            calls,
            [["docker", "image", "inspect", "shelldsl-py-3-14"]],
        )


if __name__ == "__main__":
    unittest.main()
