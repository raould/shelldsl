# Minimal Cross-Version VM

## Purpose

This document defines a small, generic virtual machine intended to run from Python 2.0 through current Python 3 releases.

The VM is deliberately independent of `shelldsl`. It does not know about shell commands, pipelines, HTTP, files, or any other domain. Those capabilities belong in separate libraries built on top of the VM.

The primary goal is not to reproduce Python semantics. The goal is to provide a small, stable instruction model that libraries can target without depending heavily on Python-version-specific syntax or behavior.

The compatibility target range is Python 2.0 source syntax and runtime behavior, through later Python 2 and Python 3 interpreters where the same core semantics can be maintained.

## Compatibility policy

The core implementation must use only constructs available in Python 2.0.

The core must therefore avoid:

- `class VM(object)` and other new-style-class assumptions.
- Nested functions that depend on lexical closures.
- Python 3-only syntax.
- `//` floor division.
- `except Exception as error` syntax.
- `True` and `False` as required language-level constants.
- Comprehension-scoping assumptions.
- Runtime-generated Python 3 signatures in the shared implementation.
- Arbitrary host-language callbacks as portable program instructions.

The implementation may use ordinary Python operators internally. The restriction applies to portable VM programs and libraries, not to the implementation language used to execute the VM.

This is a source-compatibility and behavioral-compatibility goal. It is not a claim that an unmodified Python 2.0 interpreter can be built or run on every modern operating system.

## Design principles

### 1. Generic core

The VM must remain domain-neutral. A shell library, a text-processing library, a data-storage library, or a mathematical library may all target the same VM.

### 2. Strict instruction model

Portable libraries use VM instructions rather than arbitrary Python callbacks. Host-language callbacks are intentionally excluded from the MVP because they become easy escape hatches for non-portable behavior.

### 3. Explicit mutable state

The VM is stateful, but its state is explicit and inspectable. The accurate description is **state-threaded VM**, not immutable VM.

A program and its execution state are separate concepts:

- A program is an instruction sequence.
- Execution state contains the program counter, stack, environment, and halt status.
- By default, each program starts with fresh execution state.
- Debugging tools may inspect state without changing the program.
- State may later be serialized and restored into a new VM.

### 4. Simple, readable instructions

The MVP uses tuples with string opcode names:

```python
("PUSH", 10)
("ADD", None)
("HALT", None)
```

String opcodes are less compact than numeric bytecode, but they are easier to inspect, generate, debug, and document. A later assembler or serializer may translate them into a more compact representation.

### 5. Explicit values

`PUSH` preserves the supplied value. The VM does not convert every value to `float`.

This avoids silently changing large integers, numeric strings, booleans, or other values. Operations that require a particular numeric interpretation must define that conversion explicitly.

For example, `DIV` may explicitly perform true division using `float()` for its operands. That is a division rule, not a general-purpose value-normalization rule.

## Core execution state

The initial state model is intentionally small:

```python
{
    "pc": 0,
    "halt": 0,
    "stack": [],
    "env": {}
}
```

The fields have the following meanings:

- `pc`: index of the next instruction.
- `halt`: integer flag; `0` means continue and `1` means stop.
- `stack`: operand stack used by instructions.
- `env`: explicit key/value storage for the running program.

The VM must not rely on Python closure variables or implicit global state for program data.

## MVP instruction set

The initial instruction set should remain small and generic.

### Data and arithmetic

- `PUSH value`: push a value onto the operand stack.
- `POP`: remove the top stack value.
- `DUP`: duplicate the top stack value.
- `ADD`: pop two values and push their sum.
- `SUB`: pop two values and push `a - b`.
- `MUL`: pop two values and push their product.
- `DIV`: pop two values and push explicit true division.
- `STORE key`: pop a value and store it in `env[key]`.
- `LOAD key`: load `env[key]` onto the stack.

### Comparisons and logic

Comparisons are explicit VM operations rather than delegated mixed-type host-language comparisons.

- `EQ`: push `1` when operands are equal, otherwise `0`.
- `LT`: push `1` when the left operand is less than the right operand, otherwise `0`.
- `GT`: push `1` when the left operand is greater than the right operand, otherwise `0`.
- `NOT`: convert a VM condition to its inverse, using `0` and `1`.

Comparison operand rules must be documented. The VM should not silently invent an ordering for unrelated types.

VM booleans are represented as integer `0` and `1`. This avoids depending on Python 2.0 having reliable `True` and `False` constants.

### Control flow

A `while` loop is not a primitive requirement. It can be represented using a condition, a conditional branch, and a backward jump.

- `JUMP target`: set `pc` to `target`.
- `JUMP_IF_FALSE target`: pop or inspect a condition and jump when it is `0`.
- `HALT`: stop execution.

A loop has the general form:

```text
condition:
    evaluate condition
    JUMP_IF_FALSE end
    body
    JUMP condition
end:
```

These two branch instructions also support `if`, `if/else`, bounded loops, and state-machine behavior without requiring Python `while` or `if` statements in portable libraries.

## Programs and labels

Instruction tuples are the public MVP representation. Human-readable libraries may use symbolic labels, but the execution loop should ultimately operate on numeric instruction positions.

A future loading or assembly step should:

1. Collect labels.
2. Reject duplicate labels.
3. Resolve jump targets.
4. Reject unresolved labels.
5. Produce the numeric instruction sequence used by the VM.

Whether label resolution is included in the first implementation remains an open implementation decision. Numeric jump targets are sufficient for the first executable prototype.

## Primitive registry

The fixed core instruction set is not intended to solve every domain problem. A generic VM may eventually support explicitly registered primitive operations.

A primitive registry must remain controlled:

- Operations have explicit names.
- The VM checks that an operation is registered before execution.
- Each primitive documents its operand and result behavior.
- A primitive that calls host-language APIs is marked as host-dependent.
- Only primitives implemented for every supported runtime are portable.

Arbitrary functions passed directly to `run()` are not portable VM programs and should not be part of the strict MVP interface.

## Error behavior

The VM needs consistent error semantics for:

- Stack underflow.
- Missing environment keys.
- Division by zero.
- Invalid operand types.
- Unknown opcodes.
- Invalid instruction shapes.
- Invalid jump targets.
- Execution-step limits, if resource limits are added.

Python 2.0-compatible exception syntax can still be used when handling errors:

```python
try:
    state = execute_instruction(state, instruction)
except:
    error = sys.exc_info()[1]
    state["halt"] = 1
```

The implementation should avoid treating every process-control exception as a normal VM failure. The exact exception policy remains to be specified.

Stack underflow must not be silently ignored by some instructions and raised by others. Each stack operation should have one documented behavior.

## Text and bytes

The compatibility layer must distinguish semantic text from raw bytes.

The intended mapping is:

- Python 3 text: `str`.
- Python 2 text: `unicode`.
- Python 3 bytes: `bytes`.
- Python 2 bytes: `str`.

The core must not use arbitrary `str(value)` conversion as a universal serialization strategy. It should explicitly define when a value is text, when it is bytes, and when encoding or decoding occurs.

The MVP supports one interpolation style: percent formatting using `%`.

Percent formatting is suitable for ordinary text construction, but it is not shell escaping. It must not be presented as a safe way to interpolate untrusted values into shell command strings. Libraries that eventually target shells should use explicit argument lists or a dedicated escaping primitive.

## State inspection and persistence

The default execution model uses fresh state for each program run. This prevents stack, environment, and halt-state leakage between independent executions.

The VM should support non-invasive debugging access to:

- Current program counter.
- Current instruction.
- Operand stack.
- Environment values.
- Halt status.

A later persistence feature may save state and restore it into a new VM. Arbitrary Python-object serialization should not be assumed to be portable. A portable state format should be restricted to documented scalar, list, dictionary, text, and byte representations.

## API compatibility strategy

The shared core should expose one explicit-argument API that parses on Python 2.0. It should not use `exec()` to generate Python 3-only function signatures.

Modern Python wrappers may be provided later in separate modules, but they are convenience layers rather than part of the portable core. Their absence must not affect execution of a portable VM program.

The old-style Python 2.0 class form must be used where classes are required:

```python
class VM:
    def __init__(self):
        self.state = {
            "pc": 0,
            "halt": 0,
            "stack": [],
            "env": {}
        }
```

Nested functions that capture enclosing locals must not be used in the core. If a callable wrapper is needed, it should be defined at module scope and receive all required state explicitly.

## Example program

The following is an illustrative straight-line program using the MVP representation:

```python
program = [
    ("PUSH", 10),
    ("PUSH", 2),
    ("DIV", None),
    ("PUSH", 3),
    ("ADD", None),
    ("HALT", None)
]
```

The expected final stack is `[8.0]` if `DIV` uses explicit true-division semantics.

A loop can be represented with numeric targets after assembly:

```text
0: PUSH 3
1: STORE counter
2: LOAD counter
3: PUSH 0
4: GT
5: JUMP_IF_FALSE 11
6: LOAD counter
7: PUSH 1
8: SUB
9: STORE counter
10: JUMP 2
11: HALT
```

## Deferred features

The following features should not be required for the first minimal interpreter:

- Python callback execution from portable programs.
- Generated Python 3-only signatures.
- Numeric opcode encoding.
- Subprogram `CALL` and `RETURN` instructions.
- Rich object types.
- Implicit type coercion.
- Arbitrary object serialization.
- Domain-specific operations in the VM core.
- High-level `WHILE`, `IF`, or `ELSE` instructions.

Subprogram calls may be added after the stack, comparison, branch, and jump semantics are stable. They would require a separate call stack and carefully defined return behavior.

## Testing requirements

Compatibility claims should be backed by tests rather than by syntax restrictions alone.

The test plan should cover:

- Parsing with a Python 2.0-compatible parser or interpreter.
- Arithmetic and explicit division behavior.
- Stack underflow.
- Environment storage and loading.
- Comparisons producing only `0` or `1`.
- Forward and backward jumps.
- Halt behavior.
- Unknown instructions.
- Text and byte boundaries.
- Fresh-state behavior.
- State inspection.
- Portable state serialization when implemented.

Python 2.0 may require a historical build environment or syntax-validation tool. The project should document which interpreters and platforms were actually tested instead of claiming universal operating-system support.

## Summary

The MVP is a small, strict, generic, state-threaded VM:

- Python 2.0-compatible core source.
- Explicit mutable execution state.
- Fresh state by default.
- Human-readable tuple instructions.
- No arbitrary callback escape hatch.
- Explicit arithmetic and comparisons.
- Boolean values represented by `0` and `1`.
- `JUMP` and `JUMP_IF_FALSE` for universal basic control flow.
- Explicit text/bytes rules.
- Percent formatting as the sole interpolation style.
- Domain-specific libraries kept outside the VM core.

This gives independent libraries a stable target without requiring the VM to know what those libraries do.
