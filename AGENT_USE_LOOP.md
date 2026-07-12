# Portable Source Validation Loop

When using this PortaPy project to create portable Python code, source changes may
need several static and runtime iterations. Static checks are a preflight
filter; interpreter execution is the final compatibility authority.

## Scope and safety

Before starting, explicitly identify the target files and record the baseline:

- Existing checker diagnostics.
- Existing local-test results.
- Existing runtime results for each configured interpreter.
- Expected cross-version differences.

Only target source files may be changed during a source-fix iteration. Changes
to SDK shims require an intentional SDK contract decision. Checker and
framework changes must not be made merely to suppress a target diagnostic.

The PortaPy tools resolve their support files from their own installation directory,
so they can be invoked from any current working directory. Set a shell
variable:

```sh
PORTAPY=/path/to/portapy
```

The current dispatcher is:

```text
python3 "$PORTAPY/scripts/checkall.py" SOURCE...
```

It accepts individual source paths. Enumerate files before invoking it when a
directory is part of the target scope.

For a target project rooted at the current directory:

```sh
find ./src -name '*.py' -print | xargs python3 \
    "$PORTAPY/scripts/checkall.py"
```

The Docker runtime wrapper is:

```text
python3 "$PORTAPY/scripts/run_docker.py" --image IMAGE [OPTIONS] -- COMMAND...
```

If `--project` is omitted, the current working directory is mounted. Use
`--project PATH` to mount a different target project. The repository's Docker
files and build context are still resolved from the PortaPy installation, not from
the current directory.

To build and run the same command against every Dockerfile-defined Python
image, use:

```text
python3 "$PORTAPY/scripts/run_docker.py" \
    --all \
    --read-only \
    --network-none \
    -- python PortaPy/test_runner.py
```

`--all` discovers `PortaPy/docker/Dockerfile.py*` in sorted order, builds a
deterministically named image for each Dockerfile, and runs the command once
in each image. Existing images are reused by default; use `--rebuild` to force
reconstruction. Containers remain ephemeral because every run uses `--rm`,
while images are retained as local build caches. This gives stateless runtime
execution without paying the image-build cost on every iteration. Image
deletion is an explicit host cleanup operation, not part of a normal test
run.

The command continues through the matrix after a build or runtime failure and
returns a nonzero status if any image fails. A failed build is an
orchestration `ERROR`; an unavailable Docker daemon is not a target runtime
result.

It mounts the selected target project at `/workspace`, sets that as the
container working directory, and runs the command supplied after `--`. The
image supplies the target interpreter; the mounted directory supplies the
target source and tests. When run from the target project directory, for
example:

```text
python3 "$PORTAPY/scripts/run_docker.py" \
    --image portapy-py-2-7 \
    --read-only \
    --network-none \
    -- python test_runner.py
```

Use `--project PATH` to mount another project directory and `--workdir PATH`
to select its container path. The wrapper passes command arguments directly
to `docker run`; it does not construct a shell command or enable a shell in
the container. Add `--rebuild` to force rebuilding matrix images; otherwise
existing images are reused. Docker being unavailable is reported as `SKIP`
by policy when the runtime matrix treats that image as optional, or as an
orchestration `ERROR` when the image is required.

## Stage 0: establish a baseline

1. Enumerate the target source files.
2. Run `checkall.py` against every target file.
3. Run the fast local tests.
4. Run the configured runtime matrix when available.
5. Save the outputs and classify existing failures before making edits.

## Stage 1: static-analysis loop

Repeat until static validation succeeds or the iteration limit is reached:

1. Run `checkall.py` against all target files.
2. Confirm that every checker completed successfully.
3. Classify each diagnostic by rule and determine whether it is a real
    violation or a checker false positive.
4. Treat diagnostic alternatives as suggestions, not automatic replacements.
    Preserve behavior, output streams, formatting, exception behavior, and
    numeric semantics.
5. Apply the smallest semantics-preserving source or approved SDK change.
6. Run the affected local test or focused regression test.
7. Repeat from step 1.

An empty diagnostic list means that a checker found no violation. It does not
prove that the source parses or behaves correctly on every target interpreter.
A checker exception, import failure, malformed diagnostic, or unreadable
input is a tooling error and must not be treated as a source pass.

Use a finite iteration limit, normally 5–10 iterations. If the limit is
reached, stop and report the remaining diagnostics, changes made, and any
suspected checker false positives.

## Stage 2: local validation

After the static loop appears clean:

1. Run `checkall.py` again against every target file.
2. Run the complete fast local test suite.
3. Stop if either step fails.

Do not proceed to runtime testing while static validation or local tests are
failing, unless the purpose is specifically to investigate a known parser or
checker limitation.

## Stage 3: runtime matrix

Run each configured interpreter or Docker image against the source and its
tests. Every runtime result must be classified as one of:

- `PASS`: completed successfully.
- `FAIL`: completed and a test failed.
- `TIMEOUT`: exceeded the wall-clock limit.
- `CRASH`: interpreter or container terminated unexpectedly.
- `SKIP`: required image or interpreter is unavailable by policy.
- `ERROR`: the orchestration or test tool could not complete normally.
- `EXPECTED_DIFFERENCE`: a documented, intentional result difference.

Runtime failures must also be assigned to one of two ownership categories:

### Category 1: portability or syntax failure

This means the target source cannot be accepted or executed consistently by a
required interpreter because of the portable-language contract. Examples
include:

- Python 2 print-statement versus Python 3 print-expression behavior.
- Unsupported syntax such as annotations, f-strings, `with`, or `async`.
- A missing SDK shim required by the portable source contract.
- A source construct that passes one interpreter but has incompatible syntax
    or semantics on another required interpreter.

Category 1 failures are part of the overall tool goal. The agent should:

1. Inspect the source, checker diagnostics, interpreter error, and traceback.
2. Determine whether the failure is a real portability issue or a checker
     false positive.
3. Apply the smallest semantics-preserving source or approved SDK change.
4. Add or update a regression fixture when the issue reveals a checker gap.
5. Re-run static checks, local tests, and the affected runtime.

### Category 2: target-program test failure

This means the source ran under the interpreter, but a test belonging to the
target program failed because its expected behavior was not met. Examples
include:

- An assertion failure in the target's own tests.
- A domain-specific output mismatch.
- Incorrect business logic or PortaPy behavior.
- A fixture, input, environment, or expected result that the target test
    intentionally controls.

Category 2 failures are primarily for the human owner of the target program.
The agent may report the failing test, command, traceback, interpreter, and
reproduction details, but must not silently change target tests or weaken
expected assertions merely to make the matrix pass. An agent may fix a
Category 2 failure only when the user explicitly asks for that program or
test behavior to be changed.

The categories are independent of the process status. For example, both of
the following are runtime `FAIL` results, but only the first is an automatic
portability-fix candidate:

```text
Python 2.7 runtime: FAIL
    category: PORTABILITY_SYNTAX
    cause: print statement is not valid under the selected source contract

Python 3.14 runtime: FAIL
    category: TARGET_TEST
    cause: target test assertion failed
```

When the interpreter cannot parse or start the target at all, first classify
the failure using the interpreter message. A source syntax incompatibility is
Category 1; a missing test dependency, broken test command, or container
setup problem is an orchestration or environment `ERROR`, not a target-test
failure.

Apply the runtime safety policy:

- No network by default.
- No Docker socket or host credentials.
- Read-only source mounts where practical.
- Wall-clock timeout.
- Output limits.
- Resource limits where supported.

## Stage 4: runtime-correction loop

For a Category 1 runtime result, or any runtime result other than `PASS` or an
approved `EXPECTED_DIFFERENCE` that the user has asked the agent to address:

1. Identify whether the cause is portable source syntax, SDK behavior, target
    test behavior, interpreter availability, or orchestration tooling.
2. Change only the appropriate target, SDK, or test component.
3. Re-run the affected interpreter or focused test.
4. Re-run Stage 1 against all target files.
5. Re-run Stage 2 completely.
6. Re-run the complete runtime matrix after the focused result is corrected.

Category 2 failures should be reported with actionable reproduction details
and then returned to the human owner unless explicitly assigned to the agent.
Runtime failures must not be “fixed” by weakening or disabling a checker
without a separately reviewed false-positive regression test.

## Completion criteria

The process is complete only when:

- All target files pass all successfully executed checkers.
- No checker or orchestration errors occurred.
- Fast local tests pass.
- Required interpreters pass the runtime matrix, or any remaining
    `TARGET_TEST` failures have been explicitly reported and handed back to the
    human owner.
- Unavailable interpreters are explicitly classified as `SKIP`.
- Cross-version differences are documented and approved.
- The final changes and validation results are recorded.
