"""Tests for the shared static AST/token inspection context."""

import os
import sys
import unittest


SRC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from checkers._support import (  # noqa: E402
    InspectionContext,
    ParseStatus,
    clear_inspection_context,
    inspection_context,
    node_position,
    parse,
    prepare_inspection_context,
    tokens,
)


class InspectionContextTests(unittest.TestCase):
    def tearDown(self):
        clear_inspection_context()

    def test_valid_source_has_ast_and_valid_status(self):
        context = prepare_inspection_context("value = 1\n", "example.py")
        self.assertIsInstance(context, InspectionContext)
        self.assertIsNotNone(context.tree)
        self.assertIsNone(context.parse_error)
        self.assertIs(context.status, ParseStatus.VALID)

    def test_context_preserves_source_and_filename(self):
        context = prepare_inspection_context("value = 1\n", "pkg/example.py")
        self.assertEqual(context.source, "value = 1\n")
        self.assertEqual(context.filename, "pkg/example.py")

    def test_tokenization_is_cached(self):
        source = "value = 1\n"
        context = prepare_inspection_context(source)
        self.assertIs(tokens(source), context.token_list)
        self.assertGreater(len(context.token_list), 0)

    def test_parsing_is_cached(self):
        source = "value = 1\n"
        context = prepare_inspection_context(source)
        self.assertIs(parse(source), context.tree)

    def test_parent_index_tracks_ast_relationships(self):
        context = prepare_inspection_context("value = 1\n")
        assignment = context.tree.body[0]
        target = assignment.targets[0]
        self.assertIs(context.parent_of(assignment), context.tree)
        self.assertIs(context.parent_of(target), assignment)

    def test_scope_index_tracks_module_function_and_class(self):
        source = "class Box:\n    def get(self):\n        return 1\n"
        context = prepare_inspection_context(source)
        box = context.tree.body[0]
        function = box.body[0]
        returned = function.body[0]
        self.assertEqual(context.scope_of(context.tree), "module")
        self.assertEqual(context.scope_of(box), "class")
        self.assertEqual(context.scope_of(function), "function")
        self.assertEqual(context.scope_of(returned), "function")

    def test_parse_error_is_distinguished_from_valid_source(self):
        context = prepare_inspection_context("if True print(1)\n")
        self.assertIsNone(context.tree)
        self.assertIsNotNone(context.parse_error)
        self.assertIs(context.status, ParseStatus.PARSE_ERROR)

    def test_tokenize_error_is_distinguished_and_partial_tokens_remain(self):
        context = prepare_inspection_context("value = (\n")
        self.assertIsNone(context.tree)
        self.assertIsNotNone(context.token_error)
        self.assertIs(context.status, ParseStatus.TOKENIZE_ERROR)
        self.assertGreater(len(context.token_list), 0)

    def test_configuration_is_retained_without_import_execution(self):
        context = prepare_inspection_context(
            "from sibling import value\n",
            "pkg/module.py",
            module_path="pkg.module",
            import_roots=["/workspace/src"],
            import_policy="explicit-only",
        )
        self.assertEqual(context.module_path, "pkg.module")
        self.assertEqual(context.import_roots, ("/workspace/src",))
        self.assertEqual(context.import_policy, "explicit-only")

    def test_context_can_be_replaced_and_cleared(self):
        first = prepare_inspection_context("first = 1\n")
        second = prepare_inspection_context("second = 2\n")
        self.assertIsNot(first, second)
        self.assertIs(inspection_context(), second)
        clear_inspection_context()
        self.assertIsNone(inspection_context())


if __name__ == "__main__":
    unittest.main()
