"""Command specifications, contexts, direct execution, and Bash support."""

import os
import shlex
import shutil
import subprocess

from .errors import CommandError
from .result import Result


DEFAULT_BASH = None


def _resolve_executable(program, env):
    if os.path.dirname(program):
        if os.path.isfile(program) and os.access(program, os.X_OK):
            return program
        return None
    return shutil.which(program, path=env.get("PATH"))


def _resolve_bash(explicit, env):
    candidate = explicit or DEFAULT_BASH or env.get("SHELLDSL_BASH") or "bash"
    resolved = _resolve_executable(candidate, env)
    if resolved is None:
        raise CommandError("Bash executable not found: %s" % candidate)
    return resolved


class Env(object):
    """Copy-on-derive environment mapping used by a command context."""

    def __init__(self, values=None):
        self._values = dict(os.environ if values is None else values)

    def as_dict(self):
        return dict(self._values)

    def with_(self, **updates):
        values = self.as_dict()
        values.update(updates)
        return Env(values)

    def __getitem__(self, key):
        return self._values[key]

    def get(self, key, default=None):
        return self._values.get(key, default)


class CommandContext(object):
    def __init__(self, cwd=None, env=None, bash=None):
        self.cwd = cwd or os.getcwd()
        self.env = env if isinstance(env, Env) else Env(env)
        self.bash = bash

    def with_(self, cwd=None, env=None, bash=None):
        return CommandContext(
            cwd=self.cwd if cwd is None else cwd,
            env=self.env if env is None else env,
            bash=self.bash if bash is None else bash,
        )

    def cd(self, path):
        return self.with_(cwd=path)

    def which(self, program):
        return _resolve_executable(program, self.env)

    def run(self, command, *args):
        return CommandSpec(command, *args, context=self).run()

    def source(self, path, executable=None):
        shell = _resolve_bash(executable or self.bash, self.env)
        script = 'set -a; . "$1"; env -0'
        try:
            process = subprocess.Popen(
                [shell, "-c", script, shell, path],
                cwd=self.cwd,
                env=self.env.as_dict(),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            stdout, stderr = process.communicate()
        except OSError as error:
            raise CommandError("could not start Bash", [shell], error)
        if process.returncode != 0:
            raise CommandError(
                "could not source %s: %s" % (path, stderr.decode("utf-8", "replace")),
                [shell, "-c", script, shell, path],
            )
        values = {}
        for item in stdout.decode("utf-8", "replace").split("\0"):
            if "=" in item:
                key, value = item.split("=", 1)
                values[key] = value
        return self.with_(env=Env(values))


class CommandSpec(object):
    def __init__(self, command, *args, **options):
        self.context = options.pop("context", None) or CommandContext()
        self.shell_executable = options.pop("shell_executable", None)
        self.use_shell = options.pop("use_shell", False)
        if options:
            raise TypeError("unexpected command options")
        if isinstance(command, (list, tuple)):
            if args:
                raise TypeError("cannot append arguments to an argument list")
            self.argv = tuple(str(value) for value in command)
        elif args:
            self.argv = tuple([str(command)] + [str(value) for value in args])
        else:
            self.argv = tuple(shlex.split(command))
        if not self.argv:
            raise CommandError("empty command")

    def __or__(self, other):
        return Pipeline([self, other])

    def which(self):
        if self.use_shell:
            return self.shell_executable
        return self.context.which(self.argv[0])

    def run(self):
        if self.use_shell:
            executable = self.shell_executable
            if executable is None:
                raise CommandError("shell executable was not selected", self.argv)
            argv = self.argv
            shell_value = self.argv[0] if len(self.argv) == 1 else " ".join(self.argv)
        else:
            executable = self.context.which(self.argv[0])
            if executable is None:
                raise CommandError("program not found: %s" % self.argv[0], self.argv)
            argv = list(self.argv)
            shell_value = False
        try:
            process = subprocess.Popen(
                shell_value if shell_value else argv,
                cwd=self.context.cwd,
                env=self.context.env.as_dict(),
                shell=self.use_shell,
                executable=executable if self.use_shell else None,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            stdout, stderr = process.communicate()
        except OSError as error:
            raise CommandError("could not start command", argv, error)
        return Result(argv, stdout, stderr, process.returncode)


class Pipeline(object):
    def __init__(self, stages):
        self.stages = tuple(stages)
        if not self.stages:
            raise CommandError("empty pipeline")
        if any(stage.use_shell for stage in self.stages):
            raise CommandError("shell commands cannot be pipeline stages")

    def __or__(self, other):
        return Pipeline(self.stages + (other,))

    def run(self):
        processes = []
        previous = None
        try:
            for stage in self.stages:
                executable = stage.context.which(stage.argv[0])
                if executable is None:
                    raise CommandError("program not found: %s" % stage.argv[0], stage.argv)
                process = subprocess.Popen(
                    list(stage.argv),
                    cwd=stage.context.cwd,
                    env=stage.context.env.as_dict(),
                    stdin=previous,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                if previous is not None:
                    previous.close()
                previous = process.stdout
                processes.append(process)
            stdout, stderr = processes[-1].communicate()
            for process in processes[:-1]:
                process.wait()
            stderr = stderr + "".join(process.stderr.read() for process in processes[:-1])
            return Result(self.stages[-1].argv, stdout, stderr, processes[-1].returncode)
        finally:
            for process in processes:
                if process.poll() is None:
                    process.kill()
                    process.wait()


def cmd(*parts):
    if len(parts) == 1 and isinstance(parts[0], CommandContext):
        return parts[0]
    return CommandSpec(parts[0], *parts[1:])


def bash(command, *args, **options):
    context = options.pop("context", None) or CommandContext()
    executable = options.pop("executable", None)
    if options:
        raise TypeError("unexpected Bash options")
    if args:
        raise TypeError("cmd.bash() accepts one shell command string")
    shell = _resolve_bash(executable or context.bash, context.env)
    return CommandSpec(
        [command],
        context=context,
        use_shell=True,
        shell_executable=shell,
    )


def bind(program, context=None):
    def invoke(*args):
        return CommandSpec(program, *args, context=context)
    return invoke


cmd.bind = bind
cmd.bash = bash
cmd.context = lambda **options: CommandContext(**options)
