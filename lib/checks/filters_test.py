#!/usr/bin/env python
"""Tests for grr.lib.rdfvalues.checks."""
from grr.lib import test_lib
from grr.lib.checks import filters
from grr.lib.rdfvalues import checks


class FilterTest(test_lib.GRRBaseTest):
  """Test filter methods and operations."""

  def testNonexistentFilterIsError(self):
    self.assertRaises(filters.DefinitionError, checks.Filter, type="NoFilter")

  def testFilter(self):
    kwargs = {"type": "ObjectFilter"}
    filt = checks.Filter(**kwargs)
    self.assertEqual(filt.type, kwargs["type"])
    self.assertIsInstance(filt, checks.Filter)
    # Ensure the filter hook is initialized as well.
    self.assertIsInstance(filt._filter, filters.ObjectFilter)

  def testFilterWithExpression(self):
    kwargs = {"type": "ObjectFilter", "expression": "do stuff"}
    filt = checks.Filter(**kwargs)
    self.assertIsInstance(filt, checks.Filter)
    self.assertEqual(filt.type, kwargs["type"])
    self.assertEqual(filt.expression, kwargs["expression"])

