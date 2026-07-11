"""Small helpers shared by independently discoverable checkers."""

import ast
import io
import tokenize


def tokens(source):
    """Return tokens, or the tokens available before an incomplete source error."""
    result = []
    try:
        for token in tokenize.generate_tokens(io.StringIO(source).readline):
            result.append(token)
    except (tokenize.TokenError, IndentationError, SyntaxError):
        pass
    return result


def parse(source):
    """Return the Python 3 AST, or None when parsing is unavailable."""
    try:
        return ast.parse(source)
    except (IndentationError, SyntaxError, TypeError, ValueError):
        return None


def node_position(node):
    """Return a one-based source position for an AST node."""
    return node.lineno, node.col_offset + 1
