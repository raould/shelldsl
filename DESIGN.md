# shelldsl MVP Design

This document defines the first host-side implementation of `shelldsl`. It is
based on [PURPOSE.md](PURPOSE.md) and the portable-source policy in
[VM/DESGIN.md](VM/DESGIN.md). The file name is intentionally `DESIGN.md` at
the repository root; the VM document remains the source-compatibility design.

## MVP boundary

The MVP is a small, zero-dependency Python host library for invoking programs
installed on the machine where the calling script runs. It is an orchestration
library, not a replacement for Python's data-processing libraries and not a
remote execution system.

The MVP must:

- Invoke any executable discoverable through the host process's `PATH`.
- Also invoke an executable supplied as an explicit path.
- Use argument lists and `shell=False` by default.
- Keep command construction lazy until `.run()` or an output property is read.
- Support explicit pipelines between command specifications.
- Return an explicit result object containing stdout, stderr, and exit code.
- Make output conversion deliberate through `.text`, `.lines`, `.json()`,
  `.csv()`, `.tsv()`, and `.kv()`.
- Expose the effective environment, working directory, and executable lookup.
- Permit isolated command contexts without mutating process-global state.
- Provide `source()` as an explicit environment-import operation.
- Avoid import hooks, namespace injection, shell-mode auto-detection, and
  third-party dependencies.

The MVP does not promise Python 2.0 execution for the host library. The
portable VM source and SDK remain governed by [VM/DESGIN.md](VM/DESGIN.md).
When the library is later split into portable and host adapters, process
creation belongs to the host adapter because Python 2.0 does not provide
`subprocess`.

## Public API

```python
from shelldsl import CommandError, Env, cmd

# Build, then run.
result = cmd("git", "status", "--short").run()
if result.ok:
    print(result.text)

# A single command string is tokenized with shlex; it is not passed to a shell.
result = cmd("git status --short").run()

# Explicit argument-list form is preferred when values are untrusted.
result = cmd(["git", "show", revision]).run()

# Inspect the host environment without executing.
print(cmd("git").which())
print(cmd.cwd)
print(cmd.env.as_dict()["PATH"])

# Bind a reusable command without import magic.
git = cmd.bind("git")
git("log", "--oneline", "-10").run()

# Lazy pipeline construction.
pipeline = cmd("ps", "aux") | cmd("grep", "python") | cmd("wc", "-l")
count = int(pipeline.run().text.strip())

# Structured output is an explicit bridge.
users = cmd("curl", "-fsS", url).run().json()
rows = cmd("cat", "sales.csv").run().csv(header=True)
config = cmd("git", "config", "--list").run().kv()

# A context is inspectable and swappable.
ctx = cmd.context(cwd=project_dir, env={"DEBUG": "1"})
ctx.run(["make", "-j4"])
```

`cmd` is a factory namespace, not a dynamic module. `cmd("program", ... )`
returns a `CommandSpec`; it does not execute a process.

## Design lessons implemented by the MVP

### 1. Explicit and inspectable environment

`CommandContext` owns the effective environment and working directory. A
context starts from a copy of `os.environ`, applies explicit overrides, and
never changes `os.environ` merely because a command is run.

The context exposes:

- `context.env`: an `Env` object with mapping behavior.
- `context.cwd`: the effective working directory.
- `context.which(program)`: executable lookup using the context's `PATH`.
- `context.with_(...)`: an immutable-style derived context.
- `context.cd(path)`: a derived context with another working directory.

`PATH` remains a string at the OS boundary. A future convenience API may offer
path-list operations, but the MVP avoids pretending that all environment
variables have a universal type.

### 2. Explicit result model

`Result` is not a string and does not implement implicit stdout coercion. It
contains:

- `argv`: the executed argument vector.
- `stdout`: decoded text.
- `stderr`: decoded text.
- `code`: the integer exit status.
- `ok`: whether `code == 0`.
- `text`: an explicit alias for stdout.
- `lines`: stdout split with `splitlines()`.
- `json()`, `csv()`, `tsv()`, and `kv()` conversion methods.

A failed process still returns a `Result`; callers decide whether to inspect
it or call `raise_for_status()`. Missing executables and process-start errors
raise `CommandError` because no process result exists.

### 3. No import magic

There is no `from shelldsl import anything` command generation, import hook,
module finder, or dynamic attribute lookup. Commands are created with `cmd()`
or `cmd.bind()`, which keeps IDE completion, static analysis, and code review
predictable.

### 4. Structured bridge methods

Parsing is opt-in and happens after execution. The MVP uses only Python's
standard library:

- `Result.json()` uses `json.loads`.
- `Result.csv()` uses `csv.reader` and returns rows or dictionaries when
  `header=True`.
- `Result.tsv()` uses the same reader with a tab delimiter.
- `Result.kv()` splits each non-empty line once at `sep` and returns a dict.

Malformed output raises the standard parser exception. The result remains
available to the caller, so parse failure is not confused with process
failure.

### 5. Unambiguous Python syntax

The library never interprets Python expressions as shell syntax. A command is
always passed through `cmd()`. A string command is tokenized with `shlex.split`
and executed without a shell. Shell operators such as `&&`, redirection, and
command substitution are not implicitly enabled.

If a user explicitly needs shell syntax, the MVP provides an opt-in
`cmd.shell(command)` constructor. It is clearly marked as shell execution and
is not used by ordinary `cmd()` calls. The implementation must document that
shell input is trusted input.

### 6. Lazy two-phase execution

`CommandSpec` and `Pipeline` are immutable descriptions. Construction performs
no executable lookup and starts no process. `.run()` is the execution boundary.
Properties that need output, such as `result.text`, belong to `Result`, not to
`CommandSpec`, so execution remains explicit.

Pipelines are also lazy. A pipeline starts all stages with OS pipes, waits for
all stages, captures the final stage's stdout, and captures stderr separately.
The pipeline result's `code` is the final stage's code in the MVP. A future
strict mode may expose every stage's status.

### 7. Explicit environment sourcing

`source(path)` runs a child shell with the requested file sourced, prints the
resulting environment as a private NUL-delimited record, and returns a derived
`CommandContext`. It does not mutate the caller's environment.

The source file is executed by the host shell, so it is trusted input. The MVP
uses `bash` when available and otherwise raises `CommandError`; shell files
are not parsed as Python.

### 8. Stable, frozen, zero-dependency core

The implementation uses only the Python standard library. No HTTP client,
terminal-color package, CLI framework, plugin system, SSH adapter, or async
runtime is included. External tools such as `curl`, `git`, and `make` remain
external programs and are resolved by the host context.

## Proposed package layout

```text
shelldsl/
    __init__.py       # public exports: cmd, Env, Result, CommandError
    core.py           # Env, CommandContext, CommandSpec, Pipeline
    result.py         # Result and output bridge methods
    errors.py         # CommandError and process-start errors
```

The first implementation may live in one module while the API is stabilized;
these boundaries describe responsibilities rather than a mandatory initial
file split.

## Skeleton implementation

The following is an implementation skeleton. It is intentionally concrete
about process, environment, and pipeline behavior while leaving packaging and
extended policy for later work.

```python
import csv
import io
import json
import os
import shlex
import shutil
import subprocess


class CommandError(Exception):
    def __init__(self, message, argv=None, cause=None):
        Exception.__init__(self, message)
        self.argv = argv
        self.cause = cause


class Env(object):
    def __init__(self, values=None):
        self._values = dict(values or os.environ)

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


class Result(object):
    def __init__(self, argv, stdout, stderr, code):
        self.argv = tuple(argv)
        self.stdout = stdout
        self.stderr = stderr
        self.code = code

    @property
    def ok(self):
        return self.code == 0

    @property
    def text(self):
        return self.stdout

    @property
    def lines(self):
        return self.stdout.splitlines()

    def raise_for_status(self):
        if not self.ok:
            raise CommandError(
                "command failed with exit code %s" % self.code,
                self.argv,
            )
        return self

    def json(self):
        return json.loads(self.stdout)

    def csv(self, header=False):
        rows = list(csv.reader(io.StringIO(self.stdout)))
        if not header:
            return rows
        if not rows:
            return []
        names = rows[0]
        return [dict(zip(names, row)) for row in rows[1:]]

    def tsv(self, columns=None):
        rows = list(csv.reader(io.StringIO(self.stdout), delimiter="\t"))
        if columns is None:
            return rows
        return [dict(zip(columns, row)) for row in rows]

    def kv(self, sep="="):
        values = {}
        for line in self.lines:
            if not line or sep not in line:
                continue
            key, value = line.split(sep, 1)
            values[key] = value
        return values


class CommandContext(object):
    def __init__(self, cwd=None, env=None):
        self.cwd = cwd or os.getcwd()
        self.env = env if isinstance(env, Env) else Env(env)

    def with_(self, cwd=None, env=None):
        return CommandContext(
            cwd=cwd or self.cwd,
            env=env or self.env,
        )

    def cd(self, path):
        return self.with_(cwd=path)

    def which(self, program):
        return shutil.which(program, path=self.env.get("PATH"))

    def run(self, command):
        return CommandSpec(command, context=self).run()

    def source(self, path):
        shell = shutil.which("bash")
        if shell is None:
            raise CommandError("source requires bash")
        marker = "__SHELLDSL_ENV__"
            script = "set -a; . \"$1\"; env -0"
        result = CommandSpec(
            [shell, "-c", script, shell, path], context=self
        ).run()
        result.raise_for_status()
        values = {}
        for item in result.stdout.split("\0"):
            if "=" in item:
                key, value = item.split("=", 1)
                values[key] = value
        return self.with_(env=Env(values))


class CommandSpec(object):
    def __init__(self, command, *args, **kwargs):
        self.context = kwargs.pop("context", None) or CommandContext()
        self.use_shell = kwargs.pop("use_shell", False)
        if kwargs:
            raise TypeError("unexpected command options")
        if isinstance(command, (list, tuple)):
            if args:
                raise TypeError("cannot append args to an argument list")
            self.argv = tuple(command)
        else:
            self.argv = tuple([command] + list(args))

    def __or__(self, other):
        return Pipeline([self, other])

    def which(self):
        if not self.argv:
            return None
        program = self.argv[0]
        if len(self.argv) == 1 and not os.path.sep in program:
            program = shlex.split(program)[0]
        return self.context.which(program)

    def run(self):
        if self.use_shell:
            argv = self.argv[0]
            executable = None
        else:
            argv = list(self.argv) if len(self.argv) > 1 else shlex.split(self.argv[0])
            if not argv:
                raise CommandError("empty command")
            executable = self.context.which(argv[0])
            if executable is None:
                raise CommandError("program not found: %s" % argv[0], argv)
        try:
            process = subprocess.Popen(
                argv,
                cwd=self.context.cwd,
                env=self.context.env.as_dict(),
                shell=self.use_shell,
                executable=executable,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
            )
            stdout, stderr = process.communicate()
        except OSError as error:
            raise CommandError("could not start command", argv, error)
        return Result(argv, stdout, stderr, process.returncode)


class Pipeline(object):
    def __init__(self, stages):
        self.stages = tuple(stages)

    def __or__(self, other):
        return Pipeline(self.stages + (other,))

    def run(self):
        processes = []
        previous = None
        try:
            for stage in self.stages:
                argv = list(stage.argv) if len(stage.argv) > 1 else shlex.split(stage.argv[0])
                if not argv or stage.context.which(argv[0]) is None:
                    raise CommandError("program not found", argv)
                process = subprocess.Popen(
                    argv,
                    cwd=stage.context.cwd,
                    env=stage.context.env.as_dict(),
                    stdin=previous,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True,
                )
                if previous is not None:
                    previous.close()
                previous = process.stdout
                processes.append(process)
            stdout, stderr = processes[-1].communicate()
            for process in processes[:-1]:
                process.wait()
            stderr_parts = [process.stderr.read() for process in processes]
            return Result(
                list(self.stages[-1].argv),
                stdout,
                "".join(stderr_parts),
                processes[-1].returncode,
            )
        finally:
            for process in processes:
                if process.poll() is None:
                    process.kill()
                    process.wait()


def cmd(*parts):
    if len(parts) == 1 and isinstance(parts[0], CommandContext):
        return parts[0]
    return CommandSpec(parts[0], *parts[1:])


def bind(program, context=None):
    def invoke(*args):
        return CommandSpec(program, *args, context=context)
    return invoke


def shell(command, context=None):
    return CommandSpec(
        command,
        context=context or CommandContext(),
        use_shell=True,
    )


_default_context = CommandContext()
cmd.env = _default_context.env
cmd.cwd = _default_context.cwd
cmd.context = lambda **options: CommandContext(**options)
cmd.bind = bind
cmd.shell = shell
```

The skeleton is deliberately an API and behavior target, not yet a claim that
all code above is production-ready. Before merging an implementation, fix the
source-environment serialization to use a dedicated helper executable or a
portable shell protocol, add Windows process handling, and test pipeline
lifecycle behavior. The MVP must never silently fall back to `shell=True`.

## Required MVP tests

The test suite must cover at least:

1. `cmd([program, argument])` invokes a known host executable.
2. `cmd("program argument")` tokenizes without shell expansion.
3. An explicit executable path works even when not found through `PATH`.
4. `which()` reflects the context's `PATH`.
5. A missing executable raises `CommandError` before process creation.
6. Non-zero commands return `Result.ok == False` and preserve stderr.
7. `.text`, `.lines`, `.json()`, `.csv()`, `.tsv()`, and `.kv()` work.
8. A pipeline passes stdout between real OS processes.
9. Derived contexts do not mutate `os.environ` or the parent context.
10. `source()` returns a derived context and does not mutate the caller.
11. Command construction does not execute until `.run()`.
12. No dynamic import or namespace command generation is required.

The VM checker suite remains a separate preflight layer. It validates portable
source; it does not prove that a host executable exists. Runtime process tests
are the final authority for this host-side MVP.

## Compatibility and safety policy

- Use explicit argument vectors for ordinary commands.
- Treat `cmd.shell(...)` and `source(...)` as trusted-input boundaries.
- Do not interpolate untrusted values into shell command strings.
- Decode process output using an explicit policy in the final implementation;
  the skeleton uses the host text mode as a placeholder.
- Preserve stderr and exit status even when a command fails.
- Never import or execute a target module merely to resolve a command.
- Keep the public API small enough to freeze before adding adapters.

## Delivery order

1. Implement `Env`, `CommandContext`, `CommandError`, and `Result`.
2. Implement non-shell `CommandSpec` with list and `shlex` forms.
3. Add `which`, context derivation, and explicit `bind`.
4. Add JSON/CSV/TSV/KV bridge methods.
5. Add pipelines and process cleanup tests.
6. Add `source()` behind host-platform tests.
7. Add the public package exports and API documentation.
8. Run the VM static checks on all portable source and the host MVP tests.

Only after these steps should shell opt-in, Windows-specific behavior, richer
pipeline status, or remote contexts be considered.
