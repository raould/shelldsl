# Portable Python Enforcement Tools

This document defines a standalone enforcement system for the restricted Python source language described in [DESGIN.md](DESGIN.md).

The tools are development and validation utilities. They are expected to run on Python 3.0 or later and do not need to run on Python 2.x. The code-under-inspection, however, must remain compatible with the project's Python 2.0-to-Python 3 portability target.

The tools must be deterministic, explainable, and independent of AI agents, LLM systems, network services, or hosted analysis APIs.

Each checker must accept source text directly. This is required for negative
tests: the suite can provide intentionally invalid programs such as
`print(f"foo")` and assert that the appropriate rules reject them without
creating or executing a source file.

## Core principle

Use a layered compatibility pipeline:

```text
source files
    |
    +--> lexical source-policy checks
    |
    +--> Python 3 AST checks
    |
    +--> optional static type checks
    |
    +--> fast local tests
    |
    +--> Docker interpreter matrix
            |
            +--> runtime result normalization
            +--> cross-version comparison
```

The static checks are a fast preflight filter. Docker execution is the final empirical compatibility test.

A lint pass must not be described as proof of portability. It means only that the source is eligible for runtime testing.

## Goals

The MVP checker system should:

- Run as ordinary standalone Python 3 programs.
- Require no AI or LLM service.
- Prefer Python standard-library dependencies.
- Report deterministic, actionable diagnostics.
- Detect common portability violations before container execution.
- Run the same source under configured interpreter images.
- Apply timeouts and resource restrictions to runtime tests.
- Normalize results before cross-version comparison.
- Distinguish static failures, runtime failures, timeouts, crashes, skips, and expected differences.

## Non-goals

The MVP does not attempt to:

- Prove arbitrary Python program equivalence.
- Reimplement the Python 2.0 parser completely in Python 3.
- Infer all runtime behavior from static source.
- Automatically repair source files.
- Import user code during static analysis.
- Depend on third-party hosted services.
- Replace domain-specific tests for shells, filesystems, processes, encodings, or external tools.

## Current checker result model

The implemented checker layer does not produce stage objects or named result
categories. Each discovered `check_source()` function returns a list:

- `[]` means that checker found no violation.
- A non-empty list contains one or more diagnostic dictionaries.

Each diagnostic contains `rule_id`, `severity`, `message`, `filename`,
`line`, `column`, and `alternatives`. The current thirty-seven rules all use
`Severity.ERROR`.

`checkall.py` combines the lists from all discovered checkers for each file and
prints every diagnostic. Its process exit status is:

- `0`: every existing input file produced no diagnostics.
- `1`: a file was missing, a file could not be read, or any checker produced a
    diagnostic.
- `2`: no input paths were provided.

For example, a clean invocation produces no diagnostic output and exits `0`:

```text
$ python3 VM/scripts/checkall.py VM/test/sdk_output_pass.py
$ echo $?
0
```

A violating invocation prints diagnostics and exits `1`:

```text
$ python3 VM/scripts/checkall.py VM/test/print_fail.py
VM/test/print_fail.py:2:5: [6d0d587] [ERROR] disallowed: 'print'. alternatives: prnt,sys.stdout.write
$ echo $?
1
```

Statuses such as `PASS`, `TIMEOUT`, `CRASH`, `SKIP`, and
`EXPECTED_DIFFERENCE` belong to the planned runtime and matrix layers. They
are not currently returned or printed by the implemented checkers.

## Tool 1: source-policy checker

The current MVP tool is the standalone Python 3 dispatcher:

```text
python3 VM/scripts/checkall.py VM/test/minimal.py
python3 VM/scripts/checkall.py VM0/src
```

It accepts individual file paths and does not execute the inspected source.
Directory traversal, standard-input support, type checking, and runtime
orchestration are not implemented by the current dispatcher.

### Programmatic source API

Each checker package under `VM/src/checkers/` must expose a source-text API in
addition to the dispatcher command-line interface. The API analyzes text
without importing, compiling for execution, or running the inspected program.

A minimal interface is:

```python
def check_source(source, filename="<string>"):
    """Return deterministic diagnostic records for source text."""
    pass
```

Each diagnostic currently contains:

```text
rule_id
severity
message
filename
line
column
alternatives
```

The API returns diagnostics instead of printing them. The CLI formats the
same records as text or machine-readable output. This keeps one checker
implementation reusable from tests, editor integrations, hooks, and the
runtime-matrix orchestrator.

`checkall.py` calls every discovered `check_source()` function and formats the
combined diagnostics. `filename` is diagnostic metadata only when source text
has already been supplied; a checker must not open or import that named file.

### CLI and string input

The command-line interface should support both paths and standard input:

The dispatcher accepts one or more source paths:

```text
python3 VM/scripts/checkall.py path/to/program.py
python3 VM/scripts/checkall.py first.py second.py
```

The command-line dispatcher and programmatic checker APIs produce equivalent
diagnostics for equivalent source text.

The dispatcher reports:

- File path.
- One-based line and column.
- Rule identifier.
- Severity.
- Short explanation.
- Suggested alternatives.

Example:

```text
VM0/src/example.py:14:5: [6d0d587] [ERROR] disallowed: 'print'. alternatives: prnt,sys.stdout.write
VM0/src/example.py:22:1: [f427411] [ERROR] disallowed: 'function or variable annotations'. alternatives: type comments
```

The dispatcher uses `sys.argv` and returns `2` when no source paths are
provided, `1` when a file is missing or any diagnostic is returned, and `0`
when every checked file returns an empty diagnostic list.

## Implemented checker behavior

The dispatcher discovers packages below `VM/src/checkers/` with
`pkgutil.iter_modules()`. A package is a checker when it exposes
`check_source(source, filename)`. Packages whose names begin with `_` are
ignored. Each checker returns a list of diagnostic dictionaries; returning
`[]` means that checker passes the source. There is no `PASS` member in the
checker severity enum.

The shared framework defines exactly three severity values:

- `Severity.ERROR`
- `Severity.WARNING`
- `Severity.INFO`

All currently implemented rules use `Severity.ERROR`. The severity value is
stored in each diagnostic and formatted as uppercase text by the dispatcher.
`PASS`, `FAIL`, `SKIP`, and similar values describe higher-level pipeline
stages only; they are not checker severities.

Token-based checkers use Python's `tokenize` module and AST-based checkers use
Python's `ast` module when parsing succeeds. A checker that cannot obtain an
AST currently returns `[]`; lexical checkers can still report findings from
tokens available before a tokenization error.

## AST checks

The current AST-based checkers parse with Python 3's `ast` module. They report
their findings when parsing succeeds and return `[]` when parsing fails. They
do not currently emit a separate parser-failure diagnostic.

## MVP rule set

Begin with a small group of high-value rules. Each rule's message must be
unique. Its stable identifier is the first seven hexadecimal characters of
the SHA-1 digest of that UTF-8 message. Registration fails on duplicate
messages and on duplicate seven-character digests.

The generated identifiers for the currently implemented rules are derived
from the SHA-1 digest of each rule message. The first seven hexadecimal
characters are used as the rule ID:

- `6d0d587`: print.
- `003d1d9`: f-string.
- `0a3b594`: floor division.
- `f427411`: function or variable annotations.
- `c4abaed`: with statement.
- `62126fd`: yield or generator syntax.
- `c58e886`: async or await syntax.
- `eec2eab`: exception binding with as.
- `0f3edd0`: raise from exception chaining.
- `312adc7`: comprehension or generator expression.
- `4695303`: set literal or set operation.
- `1a4ac84`: decorator syntax.
- `aaf0a43`: Python 2 long literal suffix.
- `0156087`: new-style class declaration.
- `9785b12`: assignment expression.
- `22f464a`: structural pattern matching.
- `1244314`: nested function definition.
- `a29656b`: nested class definition.
- `4d3a424`: global or nonlocal declaration.
- `d96b1fc`: lambda expression.
- `c514cfa`: eval() call.
- `7316fb0`: exec call.
- `38347bd`: globals() or locals() call.
- `70772ae`: wildcard import.
- `e91a391`: import inside a function.
- `d42ed99`: implicit relative import.
- `1ccb3c4`: .format() interpolation.
- `f50656d`: unsupported module import.
- `1586818`: module-level mutable state.
- `9a26b00`: unsafe shell interpolation.
- `e77202c`: arbitrary str() serialization.
- `8deafa3`: non-ASCII diagnostic literal.
- `1abe6a0`: dictionary unpacking.
- `a999712`: keyword-only arguments.
- `d0d6965`: positional-only arguments.
- `37df0c7`: True or False constant.
- `e9a50a5`: super() call.

The MVP SDK provides `shelldsl_sdk.prnt()` as a deliberately small output
shim. It accepts positional values, separates them with one space, and adds
one newline. It does not attempt to emulate Python 3's `print()` keyword
arguments or every conversion rule. The name is intentionally distinct from
`print` because Python 2.0 cannot provide Python 3 print-function semantics
for the `print(...)` syntax.

### SDK helper assessment

The SDK should remain small. A checker alternative is not automatically a
reason to add a shim: many prohibited constructs are best replaced directly
with ordinary Python 2.0 syntax. The current assessment is:

| Checker | SDK helper decision |
| --- | --- |
| `print` | **Already provided:** `prnt()` for a line and `write()` for partial output. |
| `floor division` | **Added:** `int_div(left, right)` uses `divmod()` and avoids `//` syntax. |
| `function or variable annotations` | No helper; use type comments. |
| `with statement` | No helper; use explicit `try`/`finally`. |
| `yield or generator syntax` | No helper; use an explicit list and loop. |
| `async or await syntax` | No helper; use synchronous functions or external processes. |
| `exception binding with as` | **Added:** `exception_value()` wraps `sys.exc_info()[1]`. |
| `raise from exception chaining` | No helper; raise the original exception or use an explicit error result. |
| `comprehension or generator expression` | No helper; use an explicit loop. |
| `set literal or set operation` | No helper; use a list or dictionary where the contract permits. |
| `decorator syntax` | No helper; apply an explicit wrapper call. |
| `Python 2 long literal suffix` | No helper; use an ordinary integer literal. |
| `new-style class declaration` | No helper; use the old-style class form. |
| `assignment expression` | No helper; use a separate assignment statement. |
| `structural pattern matching` | No helper; use `if` and `elif`. |
| `nested function definition` | No helper; move the function to module scope and pass state. |
| `nested class definition` | No helper; move the class to module scope. |
| `global or nonlocal declaration` | No helper; pass explicit mutable state. |
| `lambda expression` | No helper; use a named function. |
| `eval() call` | No helper; parse data explicitly. |
| `exec call` | No helper; call an explicit function or command. |
| `globals() or locals() call` | No helper; pass an explicit dictionary. |
| `wildcard import` | No helper; import names explicitly. |
| `import inside a function` | No helper; use module-level imports. |
| `implicit relative import` | No helper; use an explicit supported import form. |
| `.format() interpolation` | No helper; use `%` formatting. |
| `unsupported module import` | No helper; expand the verified allowlist deliberately. |
| `module-level mutable state` | No helper; create state inside a function. |
| `unsafe shell interpolation` | Defer a `cmd()` API until the shell boundary contract is designed. |
| `arbitrary str() serialization` | No generic helper; choose an explicit serialization format at each boundary. |
| `non-ASCII diagnostic literal` | No helper; use ASCII or perform explicit encoding at the I/O boundary. |

The only new MVP helpers are therefore `int_div()` and
`exception_value()`. The output helpers remain `prnt()` and `write()`.

### Syntax rules

- `6d0d587`: prohibited `print` statement or print-based output.
- `0a3b594`: prohibited floor division `//`.
- `f427411`: prohibited Python 3 function or variable annotations in shared source.
- `c4abaed`: prohibited `with` statement.
- `62126fd`: prohibited `yield`, generator expression, or generator function.
- `c58e886`: prohibited `async` or `await`.
- `eec2eab`: prohibited exception binding with `as`.
- `0f3edd0`: prohibited `raise ... from ...`.
- `312adc7`: prohibited comprehension.
- `4695303`: prohibited set literal or set operation when not part of the supported contract.
- `1a4ac84`: prohibited decorator.

The twenty additional rule-based checkers, plus these five source-level
coverage checkers, are now implemented. Each has its own package under
`VM/src/checkers/`, exposes `check_source(source, filename)`, and is discovered
automatically by `checkall.py`. AST-based rules return `[]`
when Python 3 cannot parse the source; token-based rules report findings that
remain available before tokenization fails.

## Positive and negative checker tests

The checker test suite must include both programs expected to pass and
programs expected to fail. A source fixture that the checker rejects is a
successful test when rejection is expected.

### Positive example

This source should produce no error-severity diagnostics:

```python
import sys


def write_message(value):
    sys.stdout.write("value=%s\n" % value)
```

### Negative example

This source should produce the relevant prohibited-syntax diagnostics:

```python
print(f"foo")
```

Depending on the configured policy, it should produce at least:

- `6d0d587` for prohibited print-based output.
- `003d1d9` for prohibited f-string interpolation.

Tests should assert rule identifiers and severity, not merely that a generic
failure occurred. This prevents a broken checker from passing because it
rejects the source for an unrelated reason.

### Expected-failure fixture shape

Fixtures can be ordinary Python data:

```python
NEGATIVE_CASES = [
    {
        "name": "print and f-string",
        "source": "print(f\\\"foo\\\")\\n",
        "rules": ["6d0d587", "003d1d9"]
    }
]
```

The test harness calls `check_source()` directly and compares returned
diagnostic rule IDs. It must not invoke the source under test.

Every rule should have at least:

1. One minimal negative source string that triggers the rule.
2. One positive source string that looks similar but is allowed.
3. One regression case for every discovered false positive or false negative.

### Parser-failure behavior

The current AST-based checkers return `[]` when Python 3 cannot parse the
source. Token-based checkers may still return findings from tokens produced
before tokenization fails. A parse failure is not currently represented as a
separate diagnostic or severity.

## Planned import policy

Import allowlisting is not implemented by the current MVP. When it is added,
use an allowlist for the portable core rather than a denylist. A denylist
allows new or overlooked modules to enter silently.

An initial allowlist may contain only modules verified for the project's target:

```text
sys
os
string
time
math
```

The future checker should inspect import syntax without importing the target
module. Static checking must not execute import-time code from the inspected
project.

The allowlist should be configurable so separate domains can add approved adapters without changing the checker implementation.

## Rule severity

The framework supports three severity values:

- `Severity.ERROR`
- `Severity.WARNING`
- `Severity.INFO`

All thirty-seven concrete MVP rules currently register as `Severity.ERROR`.
`checkall.py` treats any returned diagnostic as a failure and treats an empty
diagnostic list (`[]`) as a pass. There is currently no warning filtering,
strict mode, or severity promotion.

## Configuration

Configuration should be data, not executable project code. A simple configuration file can define:

```text
portable.checks
portable.imports
portable.exclude
portable.warning_as_error
portable.runtime_timeout
portable.max_output
portable.docker_images
```

Configuration is not implemented by the current dispatcher. Avoid describing
the options below as available until configuration support is added.

Planned options:

```text
--strict
--exclude PATH
--allow-import MODULE
--rule RULE_ID
--ignore-rule RULE_ID
--format text|machine
--python-target 2.0
```

The current dispatcher does not print an effective configuration.

## Static type checking

Static type checking is a separate stage. The shared source should use Python-2.0-safe type comments rather than Python 3 annotations:

```python
def normalize(value):  # type: (object) -> object
    return value
```

The project may run:

1. A pinned legacy mypy configuration for the oldest verified Python-style analysis.
2. A current mypy configuration for current Python 3 development.

The checker must verify the selected legacy mypy release experimentally. It must not assume that mypy 0.971 or any later release still supports Python 2 analysis.

Type checking is planned but is not implemented in the current source-policy
MVP:

```text
checkall.py --no-types SOURCE
checkall.py --types SOURCE
```

A future type-checking stage should report mypy failures distinctly from
syntax-policy failures.

## Why lint is not enough

Lint is an effective first gate, but it cannot prove runtime compatibility. Static checks cannot reliably detect:

- Standard-library behavior differences.
- Unicode and byte behavior.
- Integer division behavior through dynamic values.
- Runtime exception differences.
- Dynamic imports.
- Runtime-generated values.
- Infinite loops.
- State-dependent bugs.
- Operating-system behavior.
- External command behavior.
- Differences in third-party dependencies.

The correct interpretation is:

```text
lint pass
    = eligible for runtime compatibility testing

container pass
    = completed successfully under one interpreter

matrix pass
    = tested behavior matched across configured interpreters
```

## Fast local tests

Before Docker execution, run fast tests with the current development interpreter. These tests should validate:

- VM instruction behavior.
- Source-policy fixtures.
- Expected diagnostics.
- Test-vector normalization.
- Rule regression cases.

Fast tests should not require Docker or network access.

Every checker bug should become a regression fixture containing:

- Source input.
- Expected rule identifiers.
- Expected severity.
- Expected line and column where stable.
- Whether parsing should succeed.

## Docker runtime matrix

After static checks pass, run the code-under-inspection under actual interpreter images.

A matrix may include:

```text
Python 2.7
Python 3.0
Python 3.6
Python 3.8
Python 3.14
```

The configured versions depend on available images and project requirements. Python 2.0 may require a historical build environment, virtual machine, or emulation and should be reported separately if it cannot run in Docker.

Each image should:

- Contain one interpreter version.
- Contain or mount the source under inspection.
- Run a project-owned test runner.
- Avoid modern test dependencies in old interpreter images.
- Return the test process exit status.
- Print interpreter metadata.
- Use a fixed working directory.

The host-side orchestrator should build or select images, run containers, collect output, and classify results. The code-under-inspection should not control the matrix logic.

## Container safety

Runtime testing must be treated as execution of untrusted or potentially defective code:

- Use `--network none` by default.
- Do not mount the Docker socket.
- Do not pass host credentials or SSH agents.
- Prefer read-only source mounts for release verification.
- Use a temporary writable directory only when needed.
- Limit memory and CPU where supported.
- Limit output size.
- Apply a wall-clock timeout.
- Avoid host PID, IPC, and privileged modes.
- Pin base images for release and CI use.

Obsolete Python images may contain known vulnerabilities. Keep them isolated and do not use them for general browsing, package installation, or production workloads.

## Runtime timeout and output limits

The orchestrator must protect itself from nonterminating or noisy programs.

At minimum, configure:

- Wall-clock timeout.
- Maximum captured stdout.
- Maximum captured stderr.
- Optional memory limit.
- Optional CPU limit.

Classify a timeout separately from a failed test:

```text
Python 2.7 runtime: TIMEOUT
```

Intentional infinite-loop tests must always use a finite execution-step limit inside the test runner as well as an outer container timeout.

## Result normalization

Do not compare raw `repr()` output across interpreter versions when it is avoidable. Represent results using a stable, restricted format.

A result record may contain:

```text
STATUS=PASS
INTERPRETER=Python 3.14.x
STACK=[8.0]
HALT=1
ERROR=
```

Normalize:

- Exception results to VM error class names.
- Text and bytes using explicit tags.
- Numeric values according to the documented numeric policy.
- Dictionaries in deterministic key order for comparison.
- Platform-specific paths and diagnostics separately from semantic results.

Comparison outcomes should be:

- `MATCH`.
- `EXPECTED_DIFFERENCE`.
- `UNEXPECTED_DIFFERENCE`.
- `MISSING_RESULT`.
- `TIMEOUT`.
- `CRASH`.

## Matrix orchestration

A standalone Python 3 `run_matrix.py` should:

1. Discover configured Dockerfiles or image definitions.
2. Build images when requested.
3. Run each image with the source and test command.
4. Apply timeout and output limits.
5. Capture exit code and output.
6. Record interpreter metadata.
7. Normalize result records.
8. Compare required versions.
9. Print a summary.
10. Return a meaningful process exit code.

A simple shell script may remain useful for local development, but the Python 3 orchestrator is preferable for portable argument handling, timeout management, structured reports, and future CI integration.

The orchestrator should not run the linter inside every image. Static checks run once on the host; interpreter containers run the code and its compatibility tests.

## Suggested MVP workflow

```text
1. Discover source files.
2. Run lexical policy checks.
3. Run AST policy checks where parsing succeeds.
4. Run optional type checks.
5. Run fast local tests.
6. Build or select configured Docker images.
7. Run the code-under-inspection in each interpreter.
8. Enforce timeouts and resource limits.
9. Normalize runtime results.
10. Compare cross-version results.
11. Produce a summary and final exit status.
```

Example success:

```text
Source policy: PASS
Type checks: PASS
Local tests: PASS
Python 2.7 runtime: PASS
Python 3.14 runtime: PASS
Cross-version comparison: PASS
```

Example failure:

```text
Source policy: PASS
Type checks: PASS
Local tests: PASS
Python 2.7 runtime: FAIL
Python 3.14 runtime: PASS
Cross-version comparison: NOT_RUN
```

## Standalone implementation strategy

The tools must be usable without an AI agent or LLM system. They should have:

- Stable command-line interfaces.
- Deterministic source rules.
- Local configuration.
- No network requirement during ordinary checks.
- Plain-text and machine-readable output modes.
- Exit codes suitable for shell scripts and CI.
- Regression fixtures for every rule.
- Versioned rule identifiers.

The source-policy checker should initially use only Python 3 standard-library modules such as:

- `ast`.
- `tokenize`.
- `os`.
- `sys`.
- `re`.
- `subprocess`.
- `time`.

If the checker must run on Python 3.0 specifically, avoid APIs introduced after that version or declare a newer minimum for the tooling separately from the code-under-inspection.

The core checker functions should be pure with respect to the filesystem and
process environment whenever source text is supplied. Given the same source,
filename, configuration, and checker version, they should return the same
diagnostics in the same order.

## MVP implementation order

1. Create the standalone command-line checker.
2. Implement file and directory discovery.
3. Implement token-based rules for `print`, `//`, long literals, and forbidden exception syntax.
4. Implement AST rules for annotations, comprehensions, nested functions, decorators, imports, and prohibited calls.
5. Add rule fixtures and checker self-tests.
6. Add an import allowlist.
7. Add optional type-check command integration.
8. Add Docker matrix orchestration.
9. Add timeout, output, and no-network controls.
10. Add result normalization and comparison.
11. Add machine-readable reports.
12. Add CI integration only after local behavior is stable.

## Completion criteria

The enforcement MVP is ready when:

- It runs independently as a Python 3 program.
- It does not import or execute inspected modules during static checks.
- It detects the initial high-value rule set.
- Every rule has passing and failing fixtures.
- It reports file, line, column, rule, and severity.
- It returns reliable exit codes.
- It distinguishes lint failures from runtime failures.
- It can run at least the configured Python 2.7 and Python 3.14 containers.
- Runtime tests have timeouts and no-network defaults.
- Cross-version results can be normalized and compared.
- Missing interpreters are reported as `SKIP`, not silently treated as passes.
- No AI, LLM, hosted service, or network analysis dependency is required.

## Summary

Lint rules are the correct fast first stage, but not the final test. The standalone enforcement system should combine:

- Token-based source checks.
- AST-based structural checks.
- Import-policy checks.
- Optional static type checking.
- Fast local tests.
- Docker interpreter execution.
- Timeouts and container isolation.
- Normalized cross-version comparison.

Static analysis quickly catches most deliberate policy violations. Docker execution empirically tests the behavior that static analysis cannot prove. Together they provide a practical and explainable portability workflow.
