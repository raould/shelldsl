"""Small, explicit host-side shell orchestration API."""

from .core import (
    DEFAULT_BASH,
    CommandContext,
    CommandSpec,
    Env,
    Pipeline,
    bash,
    bind,
    cmd,
    cmd_def,
)
from .errors import CommandError
from .result import Result

__all__ = (
    "DEFAULT_BASH",
    "CommandContext",
    "CommandError",
    "CommandSpec",
    "Env",
    "Pipeline",
    "Result",
    "bash",
    "bind",
    "cmd",
    "cmd_def",
)
