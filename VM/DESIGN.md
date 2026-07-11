# VM Design and Skeleton Implementation

This document turns [VM.md](VM.md) into an explicit MVP design. It defines the execution model, instruction contracts, validation rules, state lifecycle, and a Python 2.0-compatible skeleton implementation.

The VM is generic. It does not know about `shelldsl` or any other application domain. Domain libraries provide programs expressed as VM instructions.

## MVP goals

The MVP must provide:

- One core source file that parses with Python 2.0 and later Python 2/3 interpreters.
- A strict instruction-only execution model.
- Human-readable tuple instructions.
- Explicit mutable execution state.
- Fresh state by default for every run.
- Explicit arithmetic and comparison semantics.
- `0` and `1` as VM boolean values.
- `JUMP` and `JUMP_IF_FALSE` as the only required control-flow primitives.
- Consistent validation and runtime errors.
- No arbitrary Python callbacks in portable programs.
- A clear boundary between semantic text and raw bytes.

The MVP does not provide:

- Python 3-only generated signatures.
- `CALL` and `RETURN`.
- Arbitrary Python object serialization.
- Implicit type coercion.
- Domain-specific instructions in the core.
- A shell-command implementation.

## Proposed file layout

```text
VM/
    VM.md              Compatibility and architectural goals.
    DESIGN.md          This document: detailed design and skeleton.
    core.py            Future executable implementation.
    test_core.py       Future compatibility tests.
```

The implementation below is intentionally included in this design document first. It should be copied into `core.py` only after the instruction contracts are agreed.

## Compatibility rules for `core.py`

The shared implementation must remain parseable by Python 2.0. In particular:

- Use old-style classes: `class VM:`.
- Do not use `object` as a base class.
- Do not use nested functions that capture enclosing locals.
- Do not use annotations, f-strings, comprehensions, generators, decorators, or context managers.
- Do not use `//`.
- Do not use `except ... as ...`.
- Do not require `True` or `False`; VM conditions are `0` or `1`.
- Do not use `with`, `yield`, or Python 3-only syntax in the core.
- Use `%` formatting for the core's own diagnostic strings.
- Use explicit `sys.exc_info()` when an exception value is needed.

The VM implementation itself may use normal Python operators. The restriction applies to portable VM programs, not to the interpreter implementation.

## Execution model

A program is a sequence of two-item tuples:

```python
("OPCODE", operand)
```

Every instruction has an operand position. Instructions without an operand use `None`.

Examples:

```python
("PUSH", 10)
("ADD", None)
("JUMP", 4)
("HALT", None)
```

The execution loop follows this model:

1. Validate the complete program.
2. Create fresh state unless an explicit state was supplied.
3. Read the instruction at `state["pc"]`.
4. Execute exactly one instruction.
5. Advance or replace the program counter according to the instruction.
6. Stop when `halt` becomes `1` or the program counter reaches the end.
7. Return the state to the caller.

Errors are raised instead of being printed or silently swallowed. A higher-level application may catch them and format diagnostics.

## State contract

The state dictionary has four required fields:

```python
{
    "pc": 0,
    "halt": 0,
    "stack": [],
    "env": {}
}
```

### `pc`

The index of the next instruction. It must be an integer between `0` and `len(program)` while execution is active.

### `halt`

An integer flag. `0` means execution continues and `1` means execution has stopped.

### `stack`

A list of operands. The top of the stack is the last list element.

### `env`

A dictionary for explicit program storage. Keys and values are supplied by the program; the VM does not convert them implicitly.

A fresh state is created for each `run()` call by default. A caller may pass an existing state to resume execution, but that is explicit and opt-in.

## Instruction contracts

The following table defines the MVP instruction set.

| Instruction | Stack effect | Behavior |
|---|---|---|
| `PUSH value` | `... -> ..., value` | Push `value`. |
| `POP` | `..., value -> ...` | Discard the top value. |
| `DUP` | `..., value -> ..., value, value` | Duplicate the top value. |
| `ADD` | `a, b -> a + b` | Add two operands using host `+`. |
| `SUB` | `a, b -> a - b` | Subtract right from left. |
| `MUL` | `a, b -> a * b` | Multiply two operands. |
| `DIV` | `a, b -> float(a) / float(b)` | Perform explicit true division. |
| `STORE key` | `..., value -> ...` | Store the value in `env[key]`. |
| `LOAD key` | `... -> ..., value` | Load `env[key]`; missing keys are errors. |
| `EQ` | `a, b -> 0 or 1` | Equality comparison. |
| `LT` | `a, b -> 0 or 1` | Strict less-than comparison. |
| `GT` | `a, b -> 0 or 1` | Strict greater-than comparison. |
| `NOT` | `condition -> 0 or 1` | Invert a `0`/`1` condition. |
| `JUMP target` | unchanged | Set `pc` to `target`. |
| `JUMP_IF_FALSE target` | `condition -> ...` | Pop a condition; jump when it is `0`. |
| `HALT` | unchanged | Set `halt` to `1`. |

`ADD`, `SUB`, and `MUL` intentionally use the operand types supplied by the program. They do not normalize values to floating point.

`DIV` is the exception: it explicitly converts both operands to `float` so integer division has the same true-division behavior on Python 2.0 and Python 3.

## Comparison rules

`EQ` may compare any values for which the host equality operation is defined. Its result is normalized to integer `0` or `1`.

`LT` and `GT` must not invent an ordering for unrelated values. The skeleton permits:

- Numeric comparisons between integer and floating-point values.
- Comparisons between values of the same type.

Other combinations raise `VMTypeError`.

The numeric-type test uses runtime-derived types so the source does not need a Python 2-only `long` literal.

## Control flow

A `while` loop is represented by a condition, a conditional jump, a body, and a backward jump:

```text
condition:
    ... produce 0 or 1 ...
    JUMP_IF_FALSE end
    ... body ...
    JUMP condition
end:
    ... continue ...
```

Numeric targets are used by the first executable skeleton. Symbolic label assembly is a later layer and is not required by the execution loop.

## Validation

The skeleton validates the complete program before executing it. This prevents malformed instructions from partially mutating state.

Validation checks:

- The program is a list or tuple.
- Every instruction is a two-item tuple.
- The opcode is known.
- Jump targets are integer positions within the program.
- No instruction has an invalid operand shape.

Operand type validation that depends on runtime values occurs during execution. For example, `ADD` cannot know whether two pushed values can be added until the instruction runs.

## Error model

The skeleton defines three VM-specific errors:

- `VMError`: base class for VM failures.
- `VMValidationError`: malformed program or instruction.
- `VMRuntimeError`: failure during execution.
- `VMStackError`: stack underflow.
- `VMTypeError`: unsupported operand types.

These classes use normal class inheritance available in Python 2.0. The implementation raises instances with `VMError("message")`, which is parseable by both Python 2 and Python 3.

The VM does not catch errors inside `run()`. This keeps failures visible and lets the caller decide whether to halt, retry, log, or expose the error.

## Skeleton implementation

The following implementation is intentionally conservative. It uses no arbitrary callbacks, no nested functions, no new-style classes, and no Python 3-only syntax.

```python
import sys


_INTEGER_TYPE = type(1)
_LARGE_INTEGER_TYPE = type(1 << 32)
_FLOAT_TYPE = type(1.0)
_NUMBER_TYPES = (_INTEGER_TYPE, _LARGE_INTEGER_TYPE, _FLOAT_TYPE)


class VMError(Exception):
    pass


class VMValidationError(VMError):
    pass


class VMRuntimeError(VMError):
    pass


class VMStackError(VMRuntimeError):
    pass


class VMTypeError(VMRuntimeError):
    pass


def new_state():
    """Return a fresh, independent execution state."""
    return {
        "pc": 0,
        "halt": 0,
        "stack": [],
        "env": {}
    }


def is_integer(value):
    """Return 1 for Python 2/3 integer values, otherwise 0."""
    if isinstance(value, (_INTEGER_TYPE, _LARGE_INTEGER_TYPE)):
        return 1
    return 0


def is_number(value):
    """Return 1 for supported numeric values, otherwise 0."""
    if isinstance(value, _NUMBER_TYPES):
        return 1
    return 0


def boolean_value(value):
    """Normalize a host comparison result to a VM boolean."""
    if value:
        return 1
    return 0


class VM:
    """Strict, generic, state-threaded virtual machine."""

    def __init__(self):
        self.last_state = None

    def validate_program(self, program):
        """Validate program shape and static instruction operands."""
        if not isinstance(program, (list, tuple)):
            raise VMValidationError("program must be a list or tuple")

        index = 0
        while index < len(program):
            instruction = program[index]
            if not isinstance(instruction, tuple):
                raise VMValidationError(
                    "instruction %s must be a tuple" % index
                )
            if len(instruction) != 2:
                raise VMValidationError(
                    "instruction %s must contain two items" % index
                )

            opcode = instruction[0]
            operand = instruction[1]

            if opcode not in (
                "PUSH", "POP", "DUP", "ADD", "SUB", "MUL", "DIV",
                "STORE", "LOAD", "EQ", "LT", "GT", "NOT", "JUMP",
                "JUMP_IF_FALSE", "HALT"
            ):
                raise VMValidationError(
                    "unknown opcode %s at %s" % (str(opcode), index)
                )

            if opcode in ("JUMP", "JUMP_IF_FALSE"):
                if not is_integer(operand):
                    raise VMValidationError(
                        "jump target at %s must be an integer" % index
                    )
                if operand < 0 or operand >= len(program):
                    raise VMValidationError(
                        "jump target %s at %s is outside the program" % (
                            operand, index
                        )
                    )

            index = index + 1

        return program

    def run(self, program, state=None, max_steps=None):
        """Validate and execute a program, returning its final state."""
        self.validate_program(program)

        if state is None:
            state = new_state()

        self.validate_state(state)

        steps = 0
        while state["halt"] == 0:
            if state["pc"] >= len(program):
                state["halt"] = 1
                break

            if max_steps is not None and steps >= max_steps:
                raise VMRuntimeError("maximum execution steps exceeded")

            self.step(program, state)
            steps = steps + 1

        self.last_state = state
        return state

    def validate_state(self, state):
        """Check the required execution-state shape."""
        if not isinstance(state, dict):
            raise VMRuntimeError("state must be a dictionary")
        if "pc" not in state:
            raise VMRuntimeError("state has no program counter")
        if "halt" not in state:
            raise VMRuntimeError("state has no halt flag")
        if "stack" not in state:
            raise VMRuntimeError("state has no stack")
        if "env" not in state:
            raise VMRuntimeError("state has no environment")
        if not is_integer(state["pc"]):
            raise VMRuntimeError("state program counter must be an integer")
        if state["pc"] < 0:
            raise VMRuntimeError("state program counter cannot be negative")
        if state["halt"] != 0 and state["halt"] != 1:
            raise VMRuntimeError("state halt flag must be 0 or 1")
        if not isinstance(state["stack"], list):
            raise VMRuntimeError("state stack must be a list")
        if not isinstance(state["env"], dict):
            raise VMRuntimeError("state environment must be a dictionary")

    def step(self, program, state):
        """Execute exactly one instruction."""
        pc = state["pc"]
        instruction = program[pc]
        opcode = instruction[0]
        operand = instruction[1]
        next_pc = pc + 1

        if opcode == "PUSH":
            state["stack"].append(operand)

        elif opcode == "POP":
            self.pop_value(state)

        elif opcode == "DUP":
            value = self.peek_value(state)
            state["stack"].append(value)

        elif opcode == "ADD":
            a, b = self.pop_two(state)
            try:
                state["stack"].append(a + b)
            except Exception:
                raise VMTypeError("ADD operands are not compatible")

        elif opcode == "SUB":
            a, b = self.pop_two(state)
            try:
                state["stack"].append(a - b)
            except Exception:
                raise VMTypeError("SUB operands are not compatible")

        elif opcode == "MUL":
            a, b = self.pop_two(state)
            try:
                state["stack"].append(a * b)
            except Exception:
                raise VMTypeError("MUL operands are not compatible")

        elif opcode == "DIV":
            a, b = self.pop_two(state)
            try:
                divisor = float(b)
                if divisor == 0.0:
                    raise VMRuntimeError("division by zero")
                result = float(a) / divisor
            except VMRuntimeError:
                raise
            except Exception:
                raise VMTypeError("DIV operands must be numeric")
            state["stack"].append(result)

        elif opcode == "STORE":
            value = self.pop_value(state)
            state["env"][operand] = value

        elif opcode == "LOAD":
            if operand not in state["env"]:
                raise VMRuntimeError("missing environment key %s" % str(operand))
            state["stack"].append(state["env"][operand])

        elif opcode == "EQ":
            a, b = self.pop_two(state)
            try:
                state["stack"].append(boolean_value(a == b))
            except Exception:
                raise VMTypeError("EQ operands cannot be compared")

        elif opcode == "LT":
            a, b = self.pop_two(state)
            self.compare_ordered(state, a, b, "LT")
            try:
                result = a < b
            except Exception:
                raise VMTypeError("LT operands cannot be compared")
            state["stack"].append(boolean_value(result))

        elif opcode == "GT":
            a, b = self.pop_two(state)
            self.compare_ordered(state, a, b, "GT")
            try:
                result = a > b
            except Exception:
                raise VMTypeError("GT operands cannot be compared")
            state["stack"].append(boolean_value(result))

        elif opcode == "NOT":
            value = self.pop_condition(state)
            if value == 0:
                state["stack"].append(1)
            else:
                state["stack"].append(0)

        elif opcode == "JUMP":
            next_pc = operand

        elif opcode == "JUMP_IF_FALSE":
            value = self.pop_condition(state)
            if value == 0:
                next_pc = operand

        elif opcode == "HALT":
            state["halt"] = 1

        state["pc"] = next_pc
        return state

    def pop_value(self, state):
        """Pop and return the top stack value."""
        if len(state["stack"]) == 0:
            raise VMStackError("stack underflow")
        return state["stack"].pop()

    def peek_value(self, state):
        """Return the top stack value without removing it."""
        if len(state["stack"]) == 0:
            raise VMStackError("stack underflow")
        return state["stack"][len(state["stack"]) - 1]

    def pop_two(self, state):
        """Pop two operands and return them in left-to-right order."""
        b = self.pop_value(state)
        a = self.pop_value(state)
        return a, b

    def pop_condition(self, state):
        """Pop and validate a VM boolean."""
        value = self.pop_value(state)
        if value != 0 and value != 1:
            raise VMTypeError("condition must be 0 or 1")
        return value

    def compare_ordered(self, state, a, b, operation):
        """Validate operands used by LT and GT."""
        if is_number(a) and is_number(b):
            return
        if type(a) == type(b):
            return
        raise VMTypeError("%s operands have incompatible types" % operation)


def run_example():
    """Run a small arithmetic example and return its final state."""
    program = [
        ("PUSH", 10),
        ("PUSH", 2),
        ("DIV", None),
        ("PUSH", 3),
        ("ADD", None),
        ("HALT", None)
    ]
    vm = VM()
    return vm.run(program)
```

## Skeleton behavior notes

### Program completion

If `pc` reaches `len(program)` without an explicit `HALT`, the skeleton sets `halt` to `1` and returns normally. An explicit `HALT` is still recommended because it makes program intent visible.

### Instruction counter

`max_steps` is optional. It is useful for preventing accidental infinite loops during development. When it is `None`, the VM does not impose a step limit.

### Errors

The skeleton does not print errors. This is deliberate. A generic VM should return control to its caller rather than assume a terminal, log format, or user interface.

A domain-specific library may catch `VMError` and convert it into its own result object, diagnostic message, or exit status.

### No callback escape hatch

The skeleton has no `run(function)` method. Portable programs are data. The execution engine interprets data. This makes it possible to inspect, validate, serialize, and replay programs without importing the library code that originally produced them.

## Example loop

The following program decrements a counter until it reaches zero. It leaves the final counter value on the stack.

```python
program = [
    ("PUSH", 3),       # 0
    ("STORE", "count"),# 1
    ("LOAD", "count"),# 2
    ("PUSH", 0),       # 3
    ("GT", None),      # 4
    ("JUMP_IF_FALSE", 11),  # 5
    ("LOAD", "count"),# 6
    ("PUSH", 1),       # 7
    ("SUB", None),     # 8
    ("STORE", "count"),# 9
    ("JUMP", 2),       # 10
    ("LOAD", "count"),# 11
    ("HALT", None)     # 12
]
```

The jump target in this example should be adjusted if the final value is intended to remain on the stack after the false branch. A clearer version that leaves the value on the stack is:

```python
program = [
    ("PUSH", 3),            # 0
    ("STORE", "count"),    # 1
    ("LOAD", "count"),     # 2
    ("PUSH", 0),            # 3
    ("GT", None),           # 4
    ("JUMP_IF_FALSE", 12),  # 5
    ("LOAD", "count"),     # 6
    ("PUSH", 1),            # 7
    ("SUB", None),          # 8
    ("STORE", "count"),    # 9
    ("JUMP", 2),            # 10
    ("PUSH", 0),            # 11
    ("LOAD", "count"),     # 12
    ("HALT", None)          # 13
]
```

The first example demonstrates why labels or an assembler are desirable. Numeric targets are correct but fragile when instructions are inserted. The MVP execution engine can remain numeric while a later assembler provides labels.

## Label assembler design

A future assembler may accept pseudo-instructions:

```python
source = [
    ("PUSH", 3),
    ("STORE", "count"),
    ("LABEL", "condition"),
    ("LOAD", "count"),
    ("PUSH", 0),
    ("GT", None),
    ("JUMP_IF_FALSE", "done"),
    ("LOAD", "count"),
    ("PUSH", 1),
    ("SUB", None),
    ("STORE", "count"),
    ("JUMP", "condition"),
    ("LABEL", "done"),
    ("HALT", None)
]
```

The assembler would produce ordinary numeric instruction tuples before the VM sees them. `LABEL` is therefore an assembler directive, not an execution opcode.

Assembler validation should reject:

- Duplicate labels.
- Unresolved label references.
- Labels used where a non-jump operand is expected.
- Invalid instruction shapes.

The assembler is intentionally outside the first execution skeleton.

## Debugging and state snapshots

The state dictionary is already suitable for basic debugging. A caller can inspect `vm.last_state` after `run()` or pass a state object explicitly to resume execution.

A future snapshot function should copy the top-level containers:

```python
def copy_state(state):
    """Make a shallow VM-state snapshot."""
    return {
        "pc": state["pc"],
        "halt": state["halt"],
        "stack": state["stack"][:],
        "env": state["env"].copy()
    }
```

This is only a debugging snapshot. It is not yet a portable serialization format. Persistence requires a restricted value model and an explicit encoding for text and bytes.

## Future primitive registry

The MVP should use only the fixed opcode set. A future registry may add domain-neutral primitives while keeping the strict model:

```text
register(name, implementation_metadata)
```

The registry must not accept arbitrary unreviewed callbacks as portable instructions. A registered operation must identify:

- Its opcode name.
- Its stack inputs and outputs.
- Its accepted value types.
- Its error behavior.
- Its portability status.
- Its serialization requirements.

A shell library could eventually register shell-related primitives, but those would remain outside the generic VM core.

## Text and formatting boundary

The VM core should not assume that every value is text. It should preserve values as supplied and leave domain-specific encoding to primitives or libraries.

For the MVP, percent formatting is the only interpolation convention:

```python
message = "value=%s" % value
```

This is a formatting convention, not a security boundary and not shell escaping. Libraries must not use it to insert untrusted values into shell command strings.

The text policy is:

- Python 2 text is represented by `unicode` where semantic text is required.
- Python 2 `str` is treated as bytes at an I/O boundary unless explicitly decoded.
- Python 3 `str` is semantic text.
- Python 3 `bytes` is raw bytes.
- Encoding and decoding must be explicit at external boundaries.

## Testing plan

The implementation should eventually have tests covering:

1. `new_state()` returns independent stack and environment objects.
2. `PUSH`, `POP`, and `DUP` work correctly.
3. Arithmetic preserves pushed values except for explicit `DIV` conversion.
4. `DIV` gives true division and rejects zero.
5. `STORE` and `LOAD` use explicit keys.
6. Comparisons return only `0` or `1`.
7. Invalid ordered comparisons raise `VMTypeError`.
8. `JUMP` and `JUMP_IF_FALSE` implement loops.
9. Programs halt explicitly and implicitly at end-of-program.
10. Invalid programs fail before execution state is mutated.
11. Stack underflow is consistent across all stack-consuming instructions.
12. `max_steps` prevents runaway programs.
13. No portable execution path accepts a Python callback.
14. The source parses on a Python 2.0-compatible parser.
15. Text and bytes remain distinguishable at the API boundary.

## Open decisions after the skeleton

The following decisions can be made after the fixed instruction loop is tested:

- Whether to add `CALL` and `RETURN` with a separate call stack.
- Whether to add a label assembler.
- Whether to add a primitive registry.
- Whether to define a portable state serialization format.
- Whether to add a compact numeric bytecode format.
- Whether to add resource limits beyond `max_steps`.

None of these should require changing the basic execution contract.
