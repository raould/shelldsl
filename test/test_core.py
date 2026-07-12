"""Basic tests for the command-context and command-specification classes."""

import os
import tempfile
import unittest

from shelldsl import CommandContext, CommandError, CommandSpec, Env, Pipeline, bind, cmd_def
from shelldsl.core import BoundCommand


class EnvTests(unittest.TestCase):
    def test_values_are_copied_and_exposed_as_a_copy(self):
        values = {"NAME": "before"}
        environment = Env(values)
        values["NAME"] = "after"

        self.assertEqual(environment["NAME"], "before")
        copied = environment.as_dict()
        copied["NAME"] = "changed"
        self.assertEqual(environment["NAME"], "before")

    def test_with_derives_without_mutating_original(self):
        original = Env({"NAME": "old", "COUNT": "1"})
        derived = original.with_(NAME="new")

        self.assertEqual(original.get("NAME"), "old")
        self.assertEqual(derived.get("NAME"), "new")
        self.assertEqual(derived["COUNT"], "1")
        self.assertEqual(derived.get("MISSING", "fallback"), "fallback")


class CommandContextTests(unittest.TestCase):
    def test_derivation_and_cd(self):
        environment = Env({"PATH": os.environ.get("PATH", "")})
        context = CommandContext(cwd="/tmp", env=environment, bash="bash")
        derived = context.with_(cwd="/", bash="sh")

        self.assertEqual(context.cwd, "/tmp")
        self.assertIs(context.env, environment)
        self.assertEqual(context.bash, "bash")
        self.assertEqual(derived.cwd, "/")
        self.assertIs(derived.env, environment)
        self.assertEqual(derived.bash, "sh")
        self.assertEqual(context.cd("/var").cwd, "/var")

    def test_which_and_run(self):
        context = CommandContext(env=Env({"PATH": os.environ["PATH"]}))
        result = context.run("printf", "context works")

        self.assertTrue(context.which("printf"))
        self.assertEqual(result.stdout, "context works")
        self.assertTrue(result.ok)

    def test_source_imports_exported_variables(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as script:
            script.write("EXPORTED_FROM_TEST=present\n")
            path = script.name
        try:
            context = CommandContext(env=Env({"PATH": os.environ["PATH"]}))
            derived = context.source(path)
            self.assertEqual(derived.env["EXPORTED_FROM_TEST"], "present")
            self.assertNotIn("EXPORTED_FROM_TEST", context.env.as_dict())
        finally:
            os.unlink(path)


class CommandSpecTests(unittest.TestCase):
    def test_accepts_string_list_and_positional_arguments(self):
        self.assertEqual(CommandSpec("printf 'hello world'").argv, ("printf", "hello world"))
        self.assertEqual(CommandSpec(["printf", "value"], context=CommandContext()).argv, ("printf", "value"))
        self.assertEqual(CommandSpec("printf", "value").argv, ("printf", "value"))

    def test_runs_and_reports_executable(self):
        specification = cmd_def("printf", "%s", "spec works")
        result = specification.run()

        self.assertTrue(specification.which())
        self.assertEqual(result.argv, ("printf", "%s", "spec works"))
        self.assertEqual(result.stdout, "spec works")

    def test_rejects_empty_or_invalid_commands(self):
        with self.assertRaises(CommandError):
            CommandSpec("")
        with self.assertRaises(TypeError):
            CommandSpec(["printf"], "extra")

    def test_pipe_operator_creates_a_pipeline(self):
        pipeline = cmd_def("printf", "hello") | cmd_def("tr", "a-z", "A-Z")

        self.assertIsInstance(pipeline, Pipeline)
        self.assertEqual(pipeline.run().stdout, "HELLO")


class PipelineTests(unittest.TestCase):
    def test_runs_multiple_stages_and_returns_last_stage_result(self):
        pipeline = Pipeline(
            [cmd_def("printf", "one\\ntwo\\n"), cmd_def("wc", "-l")]
        )
        result = pipeline.run()

        self.assertEqual(result.stdout.strip(), "2")
        self.assertEqual(result.argv, ("wc", "-l"))

    def test_rejects_empty_and_shell_stages(self):
        with self.assertRaises(CommandError):
            Pipeline([])
        shell_stage = cmd_def.bash("printf shell")
        with self.assertRaises(CommandError):
            Pipeline([shell_stage])


class BoundCommandTests(unittest.TestCase):
    def test_bound_command_runs_program_with_bound_context(self):
        context = CommandContext(env=Env({"PATH": os.environ["PATH"]}))
        command = bind("printf", context)

        self.assertIsInstance(command, BoundCommand)
        result = command("%s", "bound works")
        self.assertEqual(result.stdout, "bound works")
        self.assertIs(command.context, context)


if __name__ == "__main__":
    unittest.main()
