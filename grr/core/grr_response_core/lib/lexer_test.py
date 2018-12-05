#!/usr/bin/env python
# Copyright 2011 Google Inc. All Rights Reserved.
"""Tests the query lexer."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib import flags
from grr_response_core.lib import lexer
from grr.test_lib import test_lib


class LexerTests(test_lib.GRRBaseTest):
  """Test the query language parser."""

  def testParser(self):
    """Test parenthesis precedence."""
    # First build an AST from the expression. (Deliberately include \r\n here):
    ast = lexer.SearchParser(""" ('file name' contains "foo") and (size > 100k
or date before "2011-10")""").Parse()

    self.assertEqual(ast.operator, "and")
    self.assertEqual(ast.args[0].attribute, "file name")
    self.assertEqual(ast.args[0].operator, "contains")
    self.assertEqual(ast.args[0].args[0], "foo")
    self.assertEqual(ast.args[1].operator, "or")
    self.assertEqual(ast.args[1].args[0].attribute, "size")
    self.assertEqual(ast.args[1].args[0].operator, ">")
    self.assertEqual(ast.args[1].args[0].args[0], "100k")
    self.assertEqual(ast.args[1].args[1].attribute, "date")
    self.assertEqual(ast.args[1].args[1].operator, "before")
    self.assertEqual(ast.args[1].args[1].args[0], "2011-10")

  def testParser2(self):
    """Test operator precedence."""
    # First build an AST from the expression. (Deliberately include \r\n here):
    ast = lexer.SearchParser(""" 'file name' contains "hello" and size > 100k
or 'file name' contains "foo" and date before "2011-10" """).Parse()

    self.assertEqual(ast.operator, "or")
    self.assertEqual(ast.args[0].operator, "and")
    self.assertEqual(ast.args[0].args[0].attribute, "file name")
    self.assertEqual(ast.args[0].args[0].operator, "contains")
    self.assertEqual(ast.args[0].args[0].args[0], "hello")
    self.assertEqual(ast.args[0].args[1].attribute, "size")
    self.assertEqual(ast.args[0].args[1].operator, ">")
    self.assertEqual(ast.args[0].args[1].args[0], "100k")

    self.assertEqual(ast.args[1].operator, "and")
    self.assertEqual(ast.args[1].args[0].attribute, "file name")
    self.assertEqual(ast.args[1].args[0].operator, "contains")
    self.assertEqual(ast.args[1].args[0].args[0], "foo")
    self.assertEqual(ast.args[1].args[1].attribute, "date")
    self.assertEqual(ast.args[1].args[1].operator, "before")
    self.assertEqual(ast.args[1].args[1].args[0], "2011-10")

  def testParser3(self):
    """Test quote escaping in strings."""
    # The following has an escaped quote.
    ast = lexer.SearchParser(r"""subject matches '"hello" \'world\''""").Parse()

    self.assertEqual(ast.operator, "matches")
    self.assertEqual(ast.args[0], """\"hello" 'world'""")

  def testFailedParser(self):
    """Test that the parser raises for invalid input."""
    # Some illegal expressions
    for expression in (
        """filename contains "foo""",  # Unterminated string
        """(filename contains "foo" """,  # Unbalanced parenthesis
        """filename contains foo or """):  # empty right expression
      parser = lexer.SearchParser(expression)
      self.assertRaises(lexer.ParseError, parser.Parse)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
