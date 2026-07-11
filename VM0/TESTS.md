# VM Test Suite

This document defines a test strategy for the generic VM described in [VM.md](VM.md) and [DESIGN.md](DESIGN.md).

The suite has two primary purposes:

1. Verify that the core source can be parsed and executed across the supported Python history, including the required Python 2.0 target.
2. Find semantic, state-management, validation, and boundary bugs that may be hidden by simple arithmetic examples.

The VM is intentionally generic. Tests in this document must test VM behavior, not shell commands or `shelldsl` behavior. Domain-specific libraries should add their own test suites on top of these tests.

## Test policy

The compatibility claim should be split into independently testable claims:

- **Source compatibility:** the core source is accepted by the target interpreter or parser.
- **Behavioral compatibility:** the same valid program produces the same state and result.
- **Failure compatibility:** invalid programs fail with the same documented VM error category.
- **Persistence compatibility:** saved state, when implemented, can be restored according to the documented format.
- **Platform compatibility:** process, terminal, filesystem, and encoding behavior are tested separately by domain libraries.

Do not claim that Python 2.0 code runs on every modern operating system merely because it passes a newer interpreter's tests. Python 2.0 may require a historical build environment or syntax-validation tool.

## Recommended repository layout

```text
VM/
    VM.md
    DESIGN.md
    TESTS.md

VM/test/
    core.py                 # Python 2.0-compatible implementation
    test_core.py            # Python 2.0-compatible behavioral tests
    test_vectors.py         # Version-independent program/result vectors
    run_tests.py            # Minimal test runner
    check_source.py         # Optional syntax/source checks
    fixtures/
        programs.txt        # Optional serialized test programs
        states.txt          # Optional serialized state fixtures

VM/scripts/
    test-current.sh         # Run tests with the active Python
    test-matrix.sh          # Run available interpreters
    test-legacy.sh          # Run historical interpreter targets

VM/docker/
    Dockerfile.py_2_7       # Python 2.7
    Dockerifle.py_3_14      # Python 3.14

VM/ci/
    ...                      # CI-specific configurations, if supported
```

The test files intended to run on Python 2.0 must obey the same source restrictions as `core.py`. Do not use `pytest`, `unittest` features unavailable on Python 2.0, f-strings, annotations, decorators, context managers, or modern assertion helpers in that compatibility subset.

## Test layers

### Layer 0: source and repository checks

These checks do not execute VM behavior:

- Confirm that required files exist.
- Confirm that the core has no Python 3-only syntax.
- Confirm that the core does not contain forbidden constructs such as `class X(object)`, `except ... as ...`, `//`, or callback-based execution APIs.
- Confirm that source files use the expected encoding policy.
- Confirm that test vectors are deterministic and do not depend on the current directory.

These checks are useful when the oldest interpreter cannot be installed on the host machine.

### Layer 1: parser compatibility

Run the core and compatibility test files through each available target parser or interpreter.

The minimum required target is Python 2.0. The project should record one of the following outcomes for that target:

- Executed successfully on a Python 2.0 interpreter.
- Parsed successfully by a Python 2.0-compatible parser, but not executed because the interpreter environment is unavailable.
- Not tested, with the reason recorded.

A parser check is not a behavioral test. It proves only that the source is syntactically acceptable.

### Layer 2: behavioral compatibility

Run the same version-independent test vectors on every available interpreter. The preferred result is identical final state, including:

- `pc`.
- `halt`.
- Operand stack.
- Environment dictionary.
- Error category for invalid programs.

Do not compare exception message text unless the project explicitly standardizes it. Exception wording can vary between Python versions.

### Layer 3: differential testing

Run identical programs through multiple interpreters and compare normalized results. A result normalizer may represent:

- Integer and floating-point values using an explicit tagged form.
- Text and bytes using separate tags.
- Exceptions by VM error class name.
- Dictionaries in a stable key order for reporting purposes.

Differential testing is especially valuable for arithmetic, comparisons, text values, and state snapshots.

### Layer 4: stress and edge-case testing

Run malformed programs, unusual values, repeated execution, long loops, and state-resume scenarios. These tests are intended to find implementation bugs rather than merely confirm documented examples.

## Test harness recommendation

Use a project-owned minimal test runner instead of making the Python 2.0-compatible suite depend on a modern test framework.

The runner can provide four simple operations:

- `check(name, function)`: run one test and record pass/fail.
- `assert_equal(expected, actual)`: compare values.
- `assert_raises(error_type, function)`: verify an expected VM error.
- `main()`: run the registered tests and write a summary through `sys.stdout.write()`.

The runner itself must be Python 2.0-compatible. A modern wrapper may optionally run the same tests under a modern framework, but the compatibility result must not depend on that wrapper.

A minimal test style is:

```python
def test_addition():
    program = [
        ("PUSH", 2),
        ("PUSH", 3),
        ("ADD", None),
        ("HALT", None)
    ]
    state = VM().run(program)
    assert_equal([5], state["stack"])
```

If the test runner uses registration, registration should happen at module scope. Do not rely on nested test factories or closures.

## Cross-version environment setup

### Recommended development setup

Use a layered setup rather than assuming every historical interpreter can run natively on the current operating system.

1. Run the suite with the current supported Python 3 interpreter.
2. Run the suite with the newest supported Python 2 interpreter available.
3. Run the suite with intermediate interpreters when available.
4. Build or obtain a Python 2.0 environment separately.
5. Run parser checks for Python 2.0 even when behavioral execution is unavailable.
6. Compare all available interpreter results against the same test vectors.

The repository should not require network access during ordinary test execution. Interpreter installation and image construction are environment setup tasks, not VM runtime dependencies.

### Python 2.0 target

Python 2.0 is the oldest required target and the most difficult to test on a current Linux system. Recommended approaches, in order of confidence:

1. A reproducible historical build environment containing the Python 2.0 source, compiler, and compatible system libraries.
2. A container or virtual machine built from a historically compatible base system.
3. A locally maintained Python 2.0 executable used by a matrix script.
4. A Python 2.0-compatible parser or grammar checker for source validation, combined with behavioral tests on later interpreters.

The exact build recipe should be documented in a repository setup file or a separate historical-build document. Do not silently label parser-only testing as full Python 2.0 runtime testing.

Python 2.0 may not build cleanly with current compilers or modern C libraries. That is an infrastructure problem and should be reported separately from VM test failures.

### Interpreter discovery

The matrix runner should accept explicit interpreter commands rather than assuming fixed names:

```text
PYTHON20=/opt/python-2.0/bin/python
PYTHON27=python2.7
PYTHON3=python3
```

If a command is unavailable, the runner should report `SKIP: interpreter unavailable` and continue. A release or compatibility claim must separately state which targets were skipped.

### Modern tooling

Modern tools such as `tox`, `nox`, or CI matrix jobs can orchestrate newer interpreters, but they should invoke the project-owned compatibility runner. They should not force Python 2.0 to install modern packaging or test dependencies.

For Python 2.0, use the repository's plain source files and runner directly. Avoid installing dependencies into the historical environment.

### Local Docker plan on a modern Ubuntu host

On a current Ubuntu host such as Ubuntu 26.04, do not install Python 2 into the host operating system. Use Docker or another isolated container runtime to provide repeatable interpreter environments. The host only needs Docker Engine or a compatible container runtime; the VM source and test runner remain mounted or copied into the container.

The recommended approach is a separate image for each interpreter family:

```text
VM/tests/docker/
    Dockerfile.py27       # Python 2.7 behavioral runtime
    Dockerfile.py26       # Optional intermediate Python 2 runtime
    Dockerfile.py20       # Historical Python 2.0 build, if feasible
    run-matrix.sh         # Build/run configured images
```

The exact directory may be adjusted to match the repository layout. The important rule is that each image declares its base operating system, compiler, interpreter source or package, and test command.

#### Python 2.7 container

Python 2.7 is the practical first target for local container execution. Use a known image or build it from source on a pinned end-of-life distribution. Do not use an unpinned `latest` tag.

The image should:

1. Use a documented base image with a digest or an explicitly recorded release tag.
2. Install only the packages needed to run Python 2.7 and the repository test runner.
3. Copy or mount the repository's Python 2.0-compatible VM files.
4. Set the working directory to the test directory.
5. Run the dependency-free test runner directly.

An illustrative Dockerfile shape is:

```dockerfile
FROM <pinned-python-2.7-compatible-image>

WORKDIR /workspace
COPY VM /workspace/VM

CMD ["python", "VM/tests/run_tests.py"]
```

The placeholder base image is intentional. Image availability and package repositories change over time, so the project should select and record a base that can actually be pulled or built. If an old distribution's package repositories have moved, use its official archive repository or build Python 2.7 from source rather than adding random third-party repositories.

Run the image from the repository root with a command equivalent to:

```text
docker build --file VM/tests/docker/Dockerfile.py27 --tag shelldsl-vm-py27 .
docker run --rm shelldsl-vm-py27
```

The command should return the test runner's exit status. `--rm` prevents stopped test containers from accumulating. Do not run tests with host networking, host PID namespaces, or a writable host filesystem unless a particular test explicitly requires those capabilities.

#### Python 2.0 container

Python 2.0 is a different problem from Python 2.7. A current Linux container cannot normally execute a Python 2.0 binary built against an incompatible historical C library. A Dockerfile based on a modern Ubuntu release should not claim to provide Python 2.0 merely because its source code is present.

Use the following escalation plan:

1. Try a pinned historical base image whose CPU architecture and C library are compatible with Python 2.0.
2. If no suitable image exists, build Python 2.0 inside a historically appropriate userspace image with the required compiler and libraries.
3. If the host architecture cannot execute the historical binary, run the container under the appropriate emulation layer, such as QEMU, and record that fact.
4. If Docker execution remains impractical, use a small virtual machine or a reproducible historical build environment for the Python 2.0 runtime.
5. Always run the source parser check separately, even when Python 2.0 behavioral execution is unavailable.

The Python 2.0 image should be treated as a historical artifact. Pin the base image by digest where possible, record the source archive checksum, and document compiler and library versions. Do not use `apt-get upgrade` in this image: moving historical packages forward can make the build non-reproducible or impossible.

An illustrative shape is:

```dockerfile
FROM <pinned-historical-build-image>

# Install only the historically required compiler and libraries.
# Copy a checksum-verified Python 2.0 source archive.
# Build and install Python 2.0 into /opt/python-2.0.

WORKDIR /workspace
COPY VM /workspace/VM

CMD ["/opt/python-2.0/bin/python", "VM/tests/run_tests.py"]
```

This Dockerfile is a plan, not a claim that a particular modern base image can build Python 2.0. The build environment must be selected through an experiment and then recorded in the repository once verified.

#### Mounting the working tree during development

For fast local iteration, mount the repository read/write and keep the image responsible only for the interpreter:

```text
docker run --rm --volume "$PWD:/workspace" --workdir /workspace \
    shelldsl-vm-py27 python VM/tests/run_tests.py
```

For release verification, prefer `COPY` during image construction. This tests the exact files included in the image and avoids accidental dependence on untracked host files.

#### Matrix wrapper

A repository-owned matrix script should build or invoke configured images in a fixed order:

```text
python3      VM/tests/run_tests.py
docker run --rm shelldsl-vm-py27 python VM/tests/run_tests.py
docker run --rm shelldsl-vm-py20 /opt/python-2.0/bin/python VM/tests/run_tests.py
```

The actual script should:

- Stop on a configured interpreter failure.
- Report unavailable images as `SKIP`, not `PASS`.
- Print the image tag and interpreter version before running tests.
- Return a nonzero status if any executed target fails.
- Record whether Python 2.0 was runtime-tested or parser-tested only.

The matrix should not require Docker for the normal Python 3 developer workflow. Docker is an additional compatibility environment, not a dependency of the VM itself.

#### Container safety and reproducibility

Compatibility images contain obsolete software and should be treated as untrusted historical environments:

- Do not expose secrets, SSH agents, or production credentials.
- Prefer no network access during test execution: `docker run --network none ...`.
- Use read-only mounts for release verification where possible.
- Pin image tags and source checksums.
- Keep package installation and test execution in separate documented steps.
- Preserve container logs and interpreter-version output in CI artifacts.

The result of a container test should identify at least:

```text
interpreter: Python 2.7.x
image: shelldsl-vm-py27@sha256:<digest>
test mode: behavioral
result: PASS
```

For Python 2.0, the report should additionally identify the historical base, architecture or emulation mode, and whether the result was runtime or parser-only.

## Version-independent test vectors

Store core programs and expected results separately from the test harness where practical. A vector contains:

- A stable name.
- A program.
- Optional initial state.
- Expected final state or error category.
- Optional execution-step limit.

Example:

```python
{
    "name": "addition",
    "program": [
        ("PUSH", 2),
        ("PUSH", 3),
        ("ADD", None),
        ("HALT", None)
    ],
    "expected_stack": [5],
    "expected_halt": 1
}
```

The vector format itself must not depend on JSON, pickle, or a modern serialization library unless those are explicitly supported by the oldest target. Plain Python literals are sufficient for the first suite.

## Basic compatibility test categories

### A. Import and construction

Verify that:

- The core module imports without side effects that require modern Python.
- The VM can be instantiated.
- A fresh VM has no stale state.
- `new_state()` returns the required fields.
- Two fresh states do not share stack or environment objects.

### B. Program loading and validation

Verify valid and invalid forms:

- Empty program.
- One-instruction program.
- List program.
- Tuple program.
- Instruction with exactly two items.
- Non-tuple instruction.
- Instruction with too few items.
- Instruction with too many items.
- Unknown opcode.
- Invalid jump operand.
- Negative jump target.
- Jump target equal to program length.
- Jump target beyond program length.

Validation tests should confirm that invalid programs fail before execution state is mutated.

### C. Stack and data instructions

Verify:

- `PUSH` preserves object identity where appropriate.
- `POP` removes only the top value.
- `DUP` duplicates the top value.
- Empty-stack `POP` fails consistently.
- Empty-stack `DUP` fails consistently.
- Values are popped in last-in-first-out order.
- `STORE` removes the value from the stack.
- `LOAD` places the stored value on the stack.
- Missing environment keys fail consistently.
- Keys are not silently converted unless the documented contract requires it.

### D. Arithmetic

Verify:

- Positive addition, subtraction, and multiplication.
- Zero operands.
- Negative operands.
- Integer operands.
- Floating-point operands.
- Mixed integer and floating-point operands.
- Large integer behavior.
- Numeric strings are not silently converted by `PUSH`.
- Incompatible operands produce `VMTypeError`.
- Division uses true division.
- Division by zero fails.
- Negative division produces the documented floating-point result.
- A failed arithmetic operation does not leave a partially pushed result.

### E. Comparison and logic

Verify:

- Equal integers produce `1`.
- Unequal integers produce `0`.
- Equal text values produce `1`.
- Same-type ordered comparisons work.
- Mixed numeric ordered comparisons work.
- Unrelated-type ordered comparisons fail.
- `NOT 0` produces `1`.
- `NOT 1` produces `0`.
- `NOT` rejects values other than `0` and `1`.
- Every comparison result is exactly integer `0` or integer `1`.

### F. Control flow

Verify:

- `HALT` stops execution.
- A program without `HALT` stops at end-of-program.
- `JUMP` skips instructions.
- Forward jumps work.
- Backward jumps work.
- `JUMP_IF_FALSE` jumps for `0`.
- `JUMP_IF_FALSE` falls through for `1`.
- `JUMP_IF_FALSE` consumes exactly one condition.
- Invalid conditions fail.
- A loop terminates at the expected state.
- `max_steps` stops an infinite loop.
- The program counter is correct after a jump.

### G. State lifecycle

Verify:

- Each default `run()` starts with fresh state.
- A caller-provided state resumes from its explicit `pc`.
- A halted state does not execute further instructions unless explicitly reset.
- Stack and environment values persist only when the caller explicitly supplies state.
- `last_state` refers to the most recent completed run according to the documented contract.
- A failed validation does not replace a previously completed state unexpectedly.

### H. Debugging and snapshots

When snapshot support exists, verify:

- A snapshot contains `pc`, `halt`, `stack`, and `env`.
- Mutating a snapshot's stack does not mutate the original stack.
- Mutating a snapshot's environment does not mutate the original environment.
- Snapshot values preserve the documented shallow/deep-copy policy.
- Debug inspection does not advance `pc` or change `halt`.

### I. Text, bytes, and formatting

Verify separately on Python 2 and Python 3:

- Semantic text is distinguishable from raw bytes.
- ASCII text survives push/store/load unchanged.
- Non-ASCII text follows the explicit encoding policy.
- Raw bytes are not implicitly decoded.
- Percent formatting works for supported text values.
- Percent formatting errors are visible and categorized.
- Formatting does not provide shell escaping.
- No implicit `str(value)` conversion is used as serialization.

These tests should avoid assuming that Python 2 `str` and Python 3 `str` have the same meaning.

## Edge-case and bug-finding categories

### 1. Boundary program counters

Test:

- `pc` at `0`.
- `pc` at the last instruction.
- `pc` equal to program length.
- `pc` greater than program length in supplied state.
- Negative `pc` in supplied state.
- Jumping to the first instruction.
- Jumping to the last valid instruction.

The VM must not accidentally use Python negative indexing to execute the wrong instruction.

### 2. Stack corruption and atomicity

For each stack-consuming instruction, test empty, one-item, and sufficient-stack cases. Verify that failures do not partially mutate the stack.

Examples:

- `ADD` with zero items.
- `ADD` with one item.
- `DIV` with a zero divisor.
- `STORE` with no value.
- `JUMP_IF_FALSE` with no condition.
- `NOT` with no condition.

The expected mutation policy must be documented. If an operation pops operands before detecting a type error, tests should record that behavior or the implementation should restore the original stack.

### 3. Aliasing and mutable values

Push a list or dictionary, duplicate it, store it, and load it. Test whether the VM intentionally preserves object identity or copies values.

At minimum verify:

- `DUP` does not unexpectedly deep-copy values.
- Fresh states do not share containers.
- State snapshots follow the documented copy policy.
- Environment entries do not unexpectedly alias the stack unless the value itself is mutable and aliasing is intentional.

### 4. Numeric oddities

Test:

- Very large integers.
- Negative zero where the runtime supports it.
- Floating-point infinity and NaN where available.
- Integer/floating-point equality.
- Division results near zero.
- Values whose string form is numeric but whose type is text.
- Boolean-like integers `0` and `1` in arithmetic and conditions.

The VM should not claim exact cross-version results for floating-point edge cases unless the behavior is deliberately specified.

### 5. Type and comparison failures

Test values from incompatible categories:

- Text versus number in `LT` and `GT`.
- Dictionary versus list.
- `None` versus number.
- Nested lists with incomparable contents.
- User-defined objects, if the VM permits them.

Each failure should be a documented `VMTypeError` or another documented VM error, not an interpreter-specific raw exception.

### 6. Instruction-shape attacks and malformed data

Test unusual opcode values:

- Empty string.
- Long string.
- Non-string opcode.
- `None` opcode.
- Objects with unusual equality behavior, if accepted by the host runtime.

Test unusual operands:

- Missing operand.
- Extra operand.
- Unhashable `STORE` key.
- Mutable jump target.
- Very large jump target.
- Text jump target.

The validator should fail deterministically without executing any preceding instruction.

### 7. Infinite and excessive execution

Test:

- `JUMP` to itself.
- A backward conditional jump that never becomes false.
- A loop whose counter overflows or changes type.
- `max_steps` equal to zero.
- `max_steps` smaller than the number of required instructions.
- A program that halts exactly at the step limit.

The test runner itself must not hang. Every intentional infinite-loop test must supply a finite step limit.

### 8. Repeated and resumed execution

Run the same program:

- Twice on the same VM with no supplied state.
- Twice with the same supplied state.
- After a failed run.
- After a halted run.
- After manually changing `pc`.

These tests find stale-state and accidental-global-state bugs.

### 9. Error-path consistency

For each documented error category, verify:

- The correct VM error class is raised.
- The error occurs at the expected instruction.
- The error does not get silently printed.
- The error does not get converted into a successful halt.
- A caller can catch it using Python 2.0-compatible syntax.
- Error message assertions use stable fragments only, if messages are tested.

### 10. Text and encoding edge cases

Test:

- Empty text.
- ASCII text.
- Non-ASCII text.
- Embedded null characters.
- Newline and carriage-return characters.
- Percent signs in formatting templates.
- Bytes that are not valid text in the selected encoding.
- Text containing `%s`, `%d`, and literal `%%`.
- Formatting with missing and extra values.

The VM core should preserve values and leave external encoding decisions to the relevant library boundary.

### 11. Resource and memory behavior

Test bounded but nontrivial programs:

- Deep stacks.
- Large environments.
- Large instruction sequences.
- Repeated `DUP` operations.
- Repeated store/load operations.
- Long finite loops.

The tests should record expected resource limits rather than requiring unlimited memory or execution time.

### 12. Cross-version semantic drift

Use differential vectors to look for differences in:

- Integer versus floating-point arithmetic.
- Equality and ordering.
- Text and bytes.
- Dictionary key behavior.
- Exception class names and inheritance.
- Object string representations used in diagnostics.

Where a difference is unavoidable, normalize it in the test harness and document the normalization.

## Fuzzing and generated programs

After deterministic tests pass, add a small generated-program test layer. It must remain bounded and reproducible.

A generator can create programs from a restricted instruction grammar:

- `PUSH` small integers.
- `ADD`, `SUB`, `MUL`, `DIV` with nonzero divisors.
- `DUP`, `POP` where stack depth is known.
- `EQ`, `LT`, `GT`, and `NOT` with compatible values.
- Forward and backward jumps with a step limit.
- `HALT`.

Record the random seed for every failure. A failing generated program should be emitted as a plain instruction list that can become a permanent regression vector.

Do not fuzz unbounded programs or arbitrary host objects in the Python 2.0 compatibility runner.

## Regression-test process

When a bug is found:

1. Reduce it to the smallest instruction sequence.
2. Record the interpreter and platform where it appeared.
3. Decide whether it is a VM bug, a compatibility difference, or an unspecified behavior.
4. Add a deterministic regression test.
5. Update the contract in `DESIGN.md` if the behavior is intentional.
6. Add the case to differential testing if it affects multiple interpreters.

A bug is not fully fixed until the regression test fails before the fix and passes after it.

## Suggested commands

The exact commands depend on the available interpreters, but the repository should support this general workflow:

```text
python run_tests.py
python2.7 run_tests.py
/opt/python-2.0/bin/python run_tests.py
```

A matrix script may iterate over configured interpreter paths. It should print one clear result per target and return a nonzero status when a configured interpreter's tests fail.

For parser-only checks, use the oldest available parser or interpreter and label the result explicitly as a syntax check rather than a runtime test.

Modern CI may run:

- Current Python 3.
- Minimum supported Python 3.
- Python 2.7, if available.
- A historical Python 2.0 job or artifact, if reproducibly available.

The project should keep the core test runner independent of CI so that the same tests can be executed locally and inside historical environments.

## Completion criteria for the MVP

The VM test suite is ready for MVP release when:

- The core and compatibility tests parse on the required Python 2.0 target or a documented Python 2.0-compatible parser.
- Behavioral tests pass on every claimed runtime that can be executed.
- Any unavailable runtime is explicitly reported rather than silently omitted.
- All fixed instruction contracts have positive and negative tests.
- Fresh-state and supplied-state behavior are covered.
- Branches and loops have bounded tests.
- Invalid programs fail before execution.
- Text/bytes tests reflect the documented policy.
- Every discovered bug has a regression test.
- The test runner itself does not require modern dependencies.
