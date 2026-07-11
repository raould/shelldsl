"""Small helpers shared by independently discoverable checkers."""

import ast
import io
import tokenize
from enum import Enum


class ParseStatus(Enum):
    VALID = "valid"
    PARSE_ERROR = "parse_error"
    TOKENIZE_ERROR = "tokenize_error"


class InspectionContext:
    """Cached static-inspection data for one source file."""

    def __init__(self, source, filename="<string>", module_path=None,
                 import_roots=None, import_policy=None):
        self.source = source
        self.filename = filename
        self.module_path = module_path
        self.import_roots = tuple(import_roots or ())
        self.import_policy = import_policy
        self.token_list = []
        self.token_error = None
        self.tree = None
        self.parse_error = None
        self.parents = {}
        self.scopes = {}
        self._tokenize_source()
        self._parse_source()
        self._index_tree()

    @property
    def status(self):
        if self.token_error is not None:
            return ParseStatus.TOKENIZE_ERROR
        if self.parse_error is not None:
            return ParseStatus.PARSE_ERROR
        return ParseStatus.VALID

    def parent_of(self, node):
        return self.parents.get(node)

    def scope_of(self, node):
        return self.scopes.get(node)

    def _tokenize_source(self):
        try:
            for token in tokenize.generate_tokens(io.StringIO(self.source).readline):
                self.token_list.append(token)
        except (tokenize.TokenError, IndentationError, SyntaxError) as error:
            self.token_error = error

    def _parse_source(self):
        try:
            self.tree = ast.parse(self.source)
        except (IndentationError, SyntaxError, TypeError, ValueError) as error:
            self.parse_error = error

    def _index_tree(self):
        if self.tree is None:
            return
        self.parents[self.tree] = None

        def visit(node, scope):
            self.scopes[node] = scope
            for child in ast.iter_child_nodes(node):
                self.parents[child] = node
                child_scope = scope
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    child_scope = "function"
                elif isinstance(child, ast.ClassDef):
                    child_scope = "class"
                self.scopes[child] = child_scope
                visit(child, child_scope)

        visit(self.tree, "module")


_ACTIVE_CONTEXT = None


def prepare_inspection_context(source, filename="<string>", **configuration):
    """Build and activate one shared context for the current source file."""
    global _ACTIVE_CONTEXT
    _ACTIVE_CONTEXT = InspectionContext(source, filename, **configuration)
    return _ACTIVE_CONTEXT


def inspection_context():
    """Return the active context, if a dispatcher has prepared one."""
    return _ACTIVE_CONTEXT


def clear_inspection_context():
    """Clear the dispatcher context after a file has been fully inspected."""
    global _ACTIVE_CONTEXT
    _ACTIVE_CONTEXT = None


def tokens(source):
    """Return tokens, or the tokens available before an incomplete source error."""
    if _ACTIVE_CONTEXT is not None and _ACTIVE_CONTEXT.source == source:
        return _ACTIVE_CONTEXT.token_list
    result = []
    try:
        for token in tokenize.generate_tokens(io.StringIO(source).readline):
            result.append(token)
    except (tokenize.TokenError, IndentationError, SyntaxError):
        pass
    return result


def parse(source):
    """Return the Python 3 AST, or None when parsing is unavailable."""
    if _ACTIVE_CONTEXT is not None and _ACTIVE_CONTEXT.source == source:
        return _ACTIVE_CONTEXT.tree
    try:
        return ast.parse(source)
    except (IndentationError, SyntaxError, TypeError, ValueError):
        return None


def node_position(node):
    """Return a one-based source position for an AST node."""
    return node.lineno, node.col_offset + 1
