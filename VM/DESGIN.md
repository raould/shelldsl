# Portable Python Core Syntax

This document defines a restricted Python source subset for the VM project.

The target is Python 2.0-compatible source syntax and behavior, while also supporting execution on later Python 2 and Python 3 interpreters.

## Purpose

The portable Python core is:

- Ordinary Python source, not a new parser.
- Restricted to syntax available in Python 2.0.
- Designed to avoid behavior differences between Python 2 and Python 3.
- Checked by source-policy checks, static analysis, and cross-version tests.

The core is an authoring contract. A file is portable only when it follows this document and passes the compatibility test suite.

## Compatibility claims

Separate the following claims:

1. **Source compatibility:** the file parses on the target interpreter.
2. **Runtime compatibility:** the operations used by the file behave consistently on supported interpreters.
3. **Library compatibility:** imported modules and APIs exist on every claimed target.
4. **Platform compatibility:** filesystem, process, terminal, encoding, and operating-system behavior is separately verified.

Python 2.0 source compatibility does not guarantee that a Python 2.0 interpreter can be built or run on every modern operating system.

## Allowed language

The shared portable source may use:

- Module-level imports.
- Module-level constants with immutable values.
- Top-level functions.
- Explicit positional function arguments.
- `return` values.
- Assignment statements.
- `if`, `elif`, and `else`.
- `while` loops.
- `for ... in ...` loops.
- `try`, `except`, `else`, and `finally`.
- `raise Exception("message")`.
- `break`, `continue`, and `pass`.
- Lists, tuples, dictionaries, strings, integers, floats, and `None`.
- Indexing and ordinary slicing.
- Basic arithmetic, comparison, membership, and boolean operators.
- `%` string formatting.
- Stable built-ins whose behavior is tested on the target interpreters.
- Explicit calls to `sys.stdout.write()` and `sys.stderr.write()`.
- The small SDK shims `shelldsl_sdk.prnt()`, `shelldsl_sdk.write()`,
    `shelldsl_sdk.prntlog()`, `shelldsl_sdk.int_div()`, and
    `shelldsl_sdk.exception_value()`.

## Portable diagnostic logging

Python 2.0 has no dependable standard logging package shared with later
Python versions. Portable diagnostics therefore use the SDK's
`shelldsl_sdk.prntlog(level, message)`, which writes to stderr using only
`sys.stderr.write()` and `%` formatting.

The SDK exposes `VERBOSE`, `DEBUG`, `WARN`, and `ERROR` levels. Output is enabled when
the message level is at least as important as the effective threshold. The
effective threshold is the more verbose of these two configured thresholds:

1. The `PRNTLOGLEVEL` environment variable.
2. The programmatic `shelldsl_sdk.set_prntlog_level(level)` setting, backed by
     the `shelldsl_sdk.PRNTLOG_LEVEL` global.

`VERBOSE` is the louder setting: if either source selects `VERBOSE`, verbose
messages are enabled even when the other source is unset or selects `DEBUG`,
`WARN`, or `ERROR`. An unset or invalid environment value does not override a
valid programmatic value. If both are unset, the default threshold is `WARN`.

For host command execution, `DEBUG` messages include the resolved shell
executable location and the final fully expanded command passed to the OS or
shell. `VERBOSE` messages include the complete environment mapping passed to
the process. Environment output is sensitive and must be explicitly enabled;
all diagnostic output goes to stderr.

Example:

```python
from shelldsl_sdk import ERROR, VERBOSE, prntlog, set_prntlog_level

set_prntlog_level(VERBOSE)
prntlog(VERBOSE, "starting operation")
prntlog(ERROR, "operation failed")
```

The logger must not write diagnostic output to stdout, must flush stderr after
each message, and must not raise a secondary exception when stderr is
unavailable. Logging is a compatibility boundary and is not a replacement
for structured program results.

Example:

```python
import sys


def add_values(left, right):  # type: (object, object) -> object
    return left + right


def write_result(value):  # type: (object) -> None
    sys.stdout.write("result=%s\n" % value)


def main():  # type: () -> None
    values = [2, 3]
    result = add_values(values[0], values[1])
    write_result(result)


main()
```

## Explicit state convention

Portable libraries should prefer top-level functions with explicit state arguments and return values:

```python
def make_state():  # type: () -> dict
    return {
        "count": 0,
        "items": []
    }


def add_item(state, item):  # type: (dict, object) -> dict
    state["items"].append(item)
    return state


def item_count(state):  # type: (dict) -> int
    return len(state["items"])
```

This convention avoids hidden mutable module state, nested closures, and version-sensitive object behavior.

Functions may mutate explicitly supplied state when that is part of the API contract. They should not depend on mutable globals or enclosing function variables.

## Classes

Classes are not prohibited, but functions and explicit state are preferred.

If a class is required, use the Python 2.0 old-style form:

```python
class Counter:
    def __init__(self):
        self.value = 0

    def increment(self):
        self.value = self.value + 1
```

Do not use:

- `class Counter(object)`.
- `super()`.
- Multiple inheritance as a portability mechanism.
- Descriptors or metaclasses.
- Properties, class decorators, or other modern class features.
- Assumptions about method-resolution details.

## Prohibited syntax

The following syntax must not appear in shared portable source:

- Function annotations.
- Variable annotations.
- `async` and `await`.
- `yield` and generators.
- `with` statements.
- `as` in exception handlers.
- `raise ... from ...`.
- `nonlocal`.
- Decorators.
- List comprehensions.
- Set comprehensions.
- Dictionary comprehensions.
- Generator expressions.
- Set literals.
- Dictionary unpacking.
- Keyword-only arguments.
- Positional-only arguments.
- F-strings.
- The walrus operator.
- Structural pattern matching.
- `print` statements or the `print()` function.
- `//` floor division.
- `True` and `False` as required constants.
- `long` literals such as `1L`.
- `super()`.
- New-style classes.
- Implicit relative imports.

Some of these features existed in later Python 2 releases, but excluding them keeps the source close to the Python 2.0 parser and avoids cross-version behavior differences.

## Control flow

Use ordinary `while` and `for` statements at this layer.

Use `while` where exact control over the loop condition matters:

```python
def count_down(value):  # type: (int) -> list
    values = []

    while value > 0:
        values.append(value)
        value = value - 1

    return values
```

Use `for` for straightforward collection traversal:

```python
def sum_values(values):  # type: (list) -> object
    total = 0

    for value in values:
        total = total + value

    return total
```

Avoid comprehensions even where a later Python 2 version supports them. Python 2 and Python 3 differ in comprehension variable scoping.

## Exception handling

Use exception syntax accepted by Python 2.0 and Python 3:

```python
import sys


def safe_divide(left, right):
    try:
        return float(left) / float(right)
    except:
        error = sys.exc_info()[1]
        return None
```

Prefer specific exception classes where they are available on every target:

```python
def load_value(values, key):
    try:
        return values[key]
    except KeyError:
        return None
```

The portable source must not use `except Exception as error`. When an exception value is needed, use `sys.exc_info()`.

A bare `except` is reserved for deliberate compatibility boundaries. It must not silently hide programming errors in ordinary library code.

## String and text policy

The portable core distinguishes semantic text from raw bytes:

- Python 2 `unicode` is semantic text.
- Python 2 `str` is treated as bytes at I/O boundaries unless explicitly decoded.
- Python 3 `str` is semantic text.
- Python 3 `bytes` is raw bytes.

The core must not use arbitrary `str(value)` as a universal serialization mechanism.

Use ASCII-safe literals for VM diagnostics and control messages unless an explicit encoding policy is present.

The only interpolation style for the MVP is `%` formatting:

```python
message = "name=%s count=%s" % (name, count)
```

Percent formatting is not shell escaping. It must not be used to place untrusted values into shell command strings. Libraries that target a shell should use explicit argument lists or a dedicated escaping boundary.

Avoid relying on `.format()` for Python 2.0-level compatibility.

## Numeric policy

Python 2 and Python 3 differ in division behavior. Use explicit true division:

```python
result = float(left) / float(right)
```

Do not use `//`.

Do not silently convert every value to `float`; preserve values unless an operation explicitly requires floating-point arithmetic.

Do not use Python 2-only long suffixes:

```python
# Not portable:
value = 100000000000000000000L
```

Use unsuffixed integer literals or explicit operations, and test large-integer behavior on every supported interpreter.

Use integer `0` and `1` for portable boolean values when the value crosses the VM or library boundary. Do not require `True` or `False` as language-level constants.

## Built-ins and standard library

Prefer stable built-ins:

- `len`.
- `range`.
- `list`.
- `tuple`.
- `dict`.
- `str`.
- `unicode` only behind a compatibility boundary.
- `int`.
- `float`.
- `type`.
- `isinstance`.
- `hasattr`.
- `getattr`.
- `setattr`.
- `repr`.

Use standard modules only when their presence and behavior are verified on Python 2.0:

- `sys`.
- `os`.
- `string`.
- `time`.
- `math`.

Do not assume the following are available in Python 2.0:

- `subprocess`.
- `json`.
- `typing`.
- `argparse`.
- `dataclasses`.
- Modern logging or packaging APIs.

A library may use a later module only in a version-specific adapter outside the shared portable core.

## Next static inspection tool

The next static tool should be a shared **AST inspection context**, not a
second standalone AST parser. The current checker suite already uses
`ast.parse()` and `ast.walk()` for annotations, comprehensions, decorators,
imports, classes, calls, and function arguments. The next layer should remove
the repeated parsing and provide consistent context to every checker.

The context should be created once per source file and contain:

- Original source text.
- Filename.
- Token stream.
- Python 3 AST when parsing succeeds.
- Parent-node relationships.
- Function, class, and module scope boundaries.
- Package and module path information when available.
- Import-policy configuration.

The existing `check_source(source, filename)` API should remain supported.
The context is an internal framework detail initially; future checkers may
consume it through shared helpers rather than parsing the same source again.

The inspection layer must distinguish these conditions:

1. Source successfully tokenized and parsed.
2. Source tokenized but Python 3 AST parsing failed because it contains
    Python 2-only syntax.
3. Tokenization failed or the checker itself failed.

Python 3 AST parse failure must not automatically mean that the source is
invalid: Python 2-only constructs may be exactly what a lexical checker is
intended to identify. Lexical findings available before a failure must be
preserved, and checker/tooling errors must remain distinct from source
diagnostics.

### Static inspection implementation order

1. Build one token and AST context per input file.
2. Add parent and scope indexes for AST-based rules.
3. Migrate existing AST checkers to use the shared context.
4. Add context-aware import resolution for implicit relative imports.
5. Add package-root and import-policy configuration.
6. Add fixtures for ambiguous sibling imports and approved absolute imports.

The import resolver must inspect module paths without importing target modules
or executing import-time code. A file-only AST checker cannot reliably
distinguish `from package import name` as an absolute import from an intended
Python 2 implicit-relative import.

## Remaining prohibited-syntax coverage plan

The current checker suite covers all prohibited syntax items that can be
determined from one source file. Implicit relative imports remain
context-dependent and are planned as a separate validation stage.

### Implement with project-context validation

**Implicit relative imports** cannot be determined reliably from one source
file. `from package import name` may be an absolute import or an intended
Python 2 implicit-relative import depending on the package layout and import
configuration. A file-only checker that rejects every level-zero
`ImportFrom` would produce unacceptable false positives.

Implement this through a separate import-resolution stage:

1. Discover the target package root and module paths.
2. Read an explicit import-policy configuration containing package roots and
    approved absolute modules.
3. Resolve each import without importing target modules or executing import
    time code.
4. Report an implicit-relative-import diagnostic when Python 2 resolution
    could select a sibling/local module but the source has no explicit relative
    marker.
5. Add fixtures containing both an ambiguous sibling import and an approved
    absolute import.

Until that context-aware stage exists, the current checker should remain
conservative and must not claim complete implicit-relative-import coverage.

### Remaining implementation order

1. Context-aware import resolution.

For each future checker or validation stage:

1. Register the rule through `add_rule()`; never hand-write its ID.
2. Add source-string positive and negative tests.
3. Run `checkall.py` against all existing fixtures.
4. Verify that SDK fixtures remain clean.
5. Record whether parser failures prevent the checker from running.

The import-resolution stage requires a package-root and configuration
contract that the current `checkall.py` command does not yet provide.

## Static typing during development

The primary purpose of static types is to find bugs while developing the VM and portable libraries. Downstream typed APIs are a secondary benefit.

Because Python 2.0 cannot parse Python 3 annotation syntax, use type comments in shared source:

```python
def normalize(value):  # type: (object) -> object
    if value is None:
        return ""
    return value
```

Do not import `typing` into shared runtime files. Run mypy from a modern development environment against the old-compatible source.

The project may maintain two type-checking configurations:

1. A pinned legacy checker, using the oldest verified mypy release and mode capable of analyzing Python 2-style source.
2. A current mypy release, checking the same source against current Python 3 semantics.

The selected legacy version must be experimentally verified. Do not assume that mypy 0.971 or any later release still supports Python 2 analysis.

For modern users, a separate `.pyi` stub may provide precise annotations without affecting Python 2 runtime parsing:

```text
VM0/src/core.py
VM0/src/core.pyi
```

The shared `.py` source remains the source of truth for runtime compatibility. The stub is optional and must not be imported by Python 2.0.

## Relationship to the instruction VM0

This restricted Python layer is higher-level than the VM0 instruction set:

```text
portable Python subset
        |
        v
portable library logic
        |
        v
VM0 instructions when serialization, replay, or strict isolation is needed
```

Not every portable Python function must be lowered into VM0 bytecode. The instruction VM0 remains the stricter representation for programs that need explicit stack behavior, state snapshots, validation, or replay.

The Python subset must not be described as automatically portable merely because it invokes the VM0. Its imports, control flow, values, and host APIs must independently follow this document.

## Enforcement plan

Every portable source file should pass:

1. A Python 2.0-compatible parser or interpreter check.
2. Python 2.7 behavioral tests.
3. Python 3 behavioral tests.
4. Current and legacy static type checks where configured.
5. A source-policy checker that rejects prohibited syntax and imports.
6. Differential tests with normalized results.

The source-policy checker should report the exact file and rule violated. It should distinguish a syntax violation from a runtime or platform incompatibility.

The tests in [VM0/TESTS.md](../VM0/TESTS.md) should cover the implementation and this source policy. A minimal file such as [VM0/test/minimal.py](../VM0/test/minimal.py), if retained as a historical example, demonstrates the intended style through its use of `sys.stdout.write()` and plain Python syntax.

## Summary

The portable Python core is a deliberately restricted Python 2.0 source subset:

- Ordinary Python, not a new language parser.
- Top-level functions and explicit state preferred.
- Old-style classes only when classes are necessary.
- No nested closures or modern syntax.
- No comprehensions.
- No `print`.
- No `//`.
- No Python 3 annotations in shared source.
- Type comments for development-time static analysis.
- `%` formatting only.
- Explicit text/bytes handling.
- Explicit true division.
- Stable built-ins and verified standard-library modules only.
- VM instructions used when stricter execution or persistence is required.
