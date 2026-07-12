# VM validation tools

This directory contains the portable-source checkers and the Docker runtime
runner used to validate a separate target Python project. The target project
is not copied into this repository. Provide its path explicitly when needed, or
run the tools from the target project directory and use their current-directory
default.

## Prerequisites

For static checking, Python 3 is required. For Docker runtime validation, the
Docker CLI and a usable Docker daemon are required. Docker images are optional
for ordinary local checker development.

The tools resolve their own support files from their installation directory,
so they can be invoked from any current working directory. The examples below
use `SHELLSDK` for the directory containing the `VM` folder:

```text
SHELLSDK=/path/to/shelldsl
```

The target project should have a directory containing its Python source and
its tests, for example:

```text
/path/to/target-project/
    src/
    test/
```

## 1. Run `checkall.py` against a target project

`checkall.py` runs every discovered checker against individual source files.
It does not recursively traverse a directory, so enumerate the target files
before invoking it.

From any directory on a POSIX host:

```sh
python3 "$SHELLSDK/VM/scripts/checkall.py" \
    /path/to/target-project/src/file_a.py \
    /path/to/target-project/src/file_b.py
```

To check every Python file below a target source directory:

```sh
python3 "$SHELLSDK/VM/scripts/checkall.py" \
    $(find /path/to/target-project/src -type f -name '*.py' -print)
```

For example, when the current directory is `/home/user1/Foobar/` and the
SDK is installed at `/home/user1/shellsdk/`:

```sh
find ./src -name '*.py' -print | xargs python3 \
    /home/user1/shellsdk/VM/scripts/checkall.py
```

A clean run produces no diagnostics and exits `0`. A diagnostic, unreadable
file, or missing file produces exit `1`. Calling the command without source
paths produces usage output and exits `2`.

Because the checker is a preflight tool, a clean result means that the
registered source rules found no violations. It does not prove that the code
runs on a Python 2.x or Python 3.x interpreter.

### Checking a target source tree from another current directory

The checker path may be absolute while target paths may be relative to the
current directory:

```sh
cd /path/to/target-project
python3 "$SHELLSDK/VM/scripts/checkall.py" \
    $(find ./src -type f -name '*.py' -print)
```

If the target project contains a generated or vendored subtree, exclude it
from the file enumeration before calling the checker.

## 2. Run target code in Dockerized Python interpreters

`run_docker.py` mounts a target project into each container at `/workspace`.
The image supplies the interpreter and operating system; the mounted target
project supplies the source and tests.

Run one already-built image:

```sh
python3 "$SHELLSDK/VM/scripts/run_docker.py" \
    --image shelldsl-py-3-14 \
    --project /path/to/target-project \
    --read-only \
    --network-none \
    -- python -m unittest discover
```

The command after `--` is passed directly to the container. It is not joined
into a shell command. The container working directory defaults to
`/workspace`, so the command above runs against the mounted target project.
Use the target project's own test command when it differs from unittest:

```sh
python3 "$SHELLSDK/VM/scripts/run_docker.py" \
    --image shelldsl-py-3-14 \
    --project /path/to/target-project \
    -- python test_runner.py
```

Use `--workdir` when the target project expects another path inside the
container:

```sh
python3 "$SHELLSDK/VM/scripts/run_docker.py" \
    --image shelldsl-py-3-14 \
    --project /path/to/target-project \
    --workdir /workspace/project \
    -- python -m unittest discover
```

`--read-only` prevents target tests from changing the mounted project. Omit
it when tests intentionally create files. `--network-none` prevents network
access and is recommended for deterministic compatibility tests.

If `--project` is omitted, the current working directory is mounted. This
makes it possible to run validation while standing in the target project:

```sh
cd /path/to/target-project
python3 "$SHELLSDK/VM/scripts/run_docker.py" \
    --image shelldsl-py-3-14 \
    --read-only \
    --network-none \
    -- python -m unittest discover
```

### Run every configured Docker image

The `--all` mode discovers every `VM/docker/Dockerfile.py*`, builds a missing
image, reuses an existing image, and runs the same target command once in each
image:

```sh
python3 "$SHELLSDK/VM/scripts/run_docker.py" \
    --all \
    --project /path/to/target-project \
    --read-only \
    --network-none \
    -- python -m unittest discover
```

The current Dockerfile-derived image names are deterministic, for example:

```text
Dockerfile.py_2_7  -> shelldsl-py-2-7
Dockerfile.py_3_14 -> shelldsl-py-3-14
```

Use `--rebuild` when a Dockerfile or its base image should be rebuilt:

```sh
python3 "$SHELLSDK/VM/scripts/run_docker.py" \
    --all \
    --rebuild \
    --project /path/to/target-project \
    -- python -m unittest discover
```

Containers are removed after execution. Images remain as local caches and are
reused on later runs. Image cleanup is deliberately separate from validation;
use the Docker CLI's normal image-management commands when disk cleanup is
needed.

## Recommended validation order

For a target project, run static and runtime validation separately:

```sh
TARGET=/path/to/target-project

python3 "$SHELLSDK/VM/scripts/checkall.py" \
    $(find "$TARGET/src" -type f -name '*.py' -print)

python3 "$SHELLSDK/VM/scripts/run_docker.py" \
    --all \
    --project "$TARGET" \
    --read-only \
    --network-none \
    -- python -m unittest discover
```

Interpret the results as follows:

- Static checker exit `0`: no registered source-policy diagnostics.
- Static checker exit `1`: source diagnostics or file/orchestration errors.
- Docker command exit `0`: the target command passed in every executed image.
- Docker command nonzero: at least one build or target command failed.
- Docker unavailable: an orchestration/environment problem, not evidence about
  target source compatibility.

Static checking is preflight. Dockerized interpreter execution is the final
authority for syntax and runtime behavior on the selected images. A Python
2.0-compatible source claim should identify whether Python 2.0 was actually
executed, parser-checked only, or unavailable.

## Safety and reproducibility

- Prefer absolute target-project paths.
- Use `--read-only` unless tests need write access.
- Use `--network-none` unless network behavior is part of the test.
- Do not mount Docker credentials, the Docker socket, or unrelated host paths.
- Pass command arguments after `--`; do not rely on shell quoting or shell
  expansion inside the runner.
- Pin Docker base-image digests for release or CI validation.
- Record the image name, interpreter version, target command, and exit status.
