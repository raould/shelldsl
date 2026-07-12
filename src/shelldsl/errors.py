"""Errors raised by shelldsl before a process result exists."""


class CommandError(Exception):
    """A command could not be resolved or started."""

    def __init__(self, message, argv=None, cause=None):
        Exception.__init__(self, message)
        if argv is None:
            argv = ()
        self.argv = tuple(argv)
        self.cause = cause
