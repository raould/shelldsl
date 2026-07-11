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
- The small SDK output shim `shelldsl_sdk.prnt()` for simple line output.

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
