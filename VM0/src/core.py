"""Minimal strict virtual machine compatible with Python 2.0 and later."""


_INTEGER_TYPE = type(1)  # type: object
_LARGE_INTEGER_TYPE = type(1 << 32)  # type: object
_FLOAT_TYPE = type(1.0)  # type: object
_NUMBER_TYPES = (_INTEGER_TYPE, _LARGE_INTEGER_TYPE, _FLOAT_TYPE)  # type: tuple


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


def new_state():  # type: () -> dict
    """Return a fresh, independent execution state."""
    return {
        "pc": 0,
        "halt": 0,
        "stack": [],
        "env": {}
    }


def is_integer(value):  # type: (object) -> int
    """Return 1 for Python 2/3 integer values, otherwise 0."""
    if isinstance(value, (_INTEGER_TYPE, _LARGE_INTEGER_TYPE)):
        return 1
    return 0


def is_number(value):  # type: (object) -> int
    """Return 1 for supported numeric values, otherwise 0."""
    if isinstance(value, _NUMBER_TYPES):
        return 1
    return 0


def boolean_value(value):  # type: (object) -> int
    """Normalize a host comparison result to a VM boolean."""
    if value:
        return 1
    return 0


class VM:
    """Strict, generic, state-threaded virtual machine."""

    OPCODES = (
        "PUSH", "POP", "DUP", "ADD", "SUB", "MUL", "DIV",
        "STORE", "LOAD", "EQ", "LT", "GT", "NOT", "JUMP",
        "JUMP_IF_FALSE", "HALT"
    )

    def __init__(self):  # type: () -> None
        self.last_state = None  # type: object

    def validate_program(self, program):  # type: (object) -> object
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

            if opcode not in self.OPCODES:
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

    def run(self, program, state=None, max_steps=None):  # type: (object, object, object) -> dict
        """Validate and execute a program, returning its final state."""
        self.validate_program(program)

        if state is None:
            state = new_state()

        self.validate_state(state)
        if state["pc"] > len(program):
            raise VMRuntimeError("state program counter is outside the program")

        steps = 0  # type: int
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

    def validate_state(self, state):  # type: (object) -> None
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

    def step(self, program, state):  # type: (object, dict) -> dict
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
                result = a + b
            except Exception:
                raise VMTypeError("ADD operands are not compatible")
            state["stack"].append(result)

        elif opcode == "SUB":
            a, b = self.pop_two(state)
            try:
                result = a - b
            except Exception:
                raise VMTypeError("SUB operands are not compatible")
            state["stack"].append(result)

        elif opcode == "MUL":
            a, b = self.pop_two(state)
            try:
                result = a * b
            except Exception:
                raise VMTypeError("MUL operands are not compatible")
            state["stack"].append(result)

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
            try:
                state["env"][operand] = value
            except Exception:
                raise VMTypeError("STORE key is not usable")

        elif opcode == "LOAD":
            try:
                value = state["env"][operand]
            except KeyError:
                raise VMRuntimeError(
                    "missing environment key %s" % str(operand)
                )
            except Exception:
                raise VMTypeError("LOAD key is not usable")
            state["stack"].append(value)

        elif opcode == "EQ":
            a, b = self.pop_two(state)
            try:
                result = a == b
            except Exception:
                raise VMTypeError("EQ operands cannot be compared")
            state["stack"].append(boolean_value(result))

        elif opcode == "LT":
            a, b = self.pop_two(state)
            self.compare_ordered(a, b, "LT")
            try:
                result = a < b
            except Exception:
                raise VMTypeError("LT operands cannot be compared")
            state["stack"].append(boolean_value(result))

        elif opcode == "GT":
            a, b = self.pop_two(state)
            self.compare_ordered(a, b, "GT")
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

    def pop_value(self, state):  # type: (dict) -> object
        """Pop and return the top stack value."""
        if len(state["stack"]) == 0:
            raise VMStackError("stack underflow")
        return state["stack"].pop()

    def peek_value(self, state):  # type: (dict) -> object
        """Return the top stack value without removing it."""
        if len(state["stack"]) == 0:
            raise VMStackError("stack underflow")
        return state["stack"][len(state["stack"]) - 1]

    def pop_two(self, state):  # type: (dict) -> tuple
        """Pop two operands and return them in left-to-right order."""
        b = self.pop_value(state)
        a = self.pop_value(state)
        return a, b

    def pop_condition(self, state):  # type: (dict) -> int
        """Pop and validate a VM boolean."""
        value = self.pop_value(state)
        if value != 0 and value != 1:
            raise VMTypeError("condition must be 0 or 1")
        return value

    def compare_ordered(self, a, b, operation):  # type: (object, object, object) -> None
        """Validate operands used by LT and GT."""
        if is_number(a) and is_number(b):
            return
        if type(a) == type(b):
            return
        raise VMTypeError(
            "%s operands have incompatible types" % operation
        )
