#!/usr/bin/env python
"""Tests for grr.lib.rdfvalues.checks."""
import collections
from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib.checks import filters
from grr.lib.rdfvalues import checks


# Just a named tuple that can be used to test objectfilter expressions.
Sample = collections.namedtuple("Sample", ["x", "y"])


class FilterTests(test_lib.GRRBaseTest):
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

  def testFilterRegistry(self):
    self.assertIsInstance(filters.Filter.GetFilter("ObjectFilter"),
                          filters.ObjectFilter)
    self.assertRaises(filters.DefinitionError, filters.Filter.GetFilter, "???")


class HandlerTests(test_lib.GRRBaseTest):
  """Test handler operations."""

  def setUp(self):
    super(HandlerTests, self).setUp()
    fx0 = checks.Filter({"type": "ObjectFilter", "expression": "x == 0"})
    fy0 = checks.Filter({"type": "ObjectFilter", "expression": "y == 0"})
    bad = checks.Filter({"type": "ObjectFilter", "expression": "y =="})
    self.ok = [fx0, fy0]
    self.bad = [fx0, fy0, bad]
    self.all = [Sample(0, 0), Sample(0, 1), Sample(1, 0), Sample(1, 1)]
    self.serial = [Sample(0, 0)]
    self.parallel = [Sample(0, 0), Sample(0, 1), Sample(1, 0)]

  def GetFilters(self, filt_defs):
    """Initialize one or more filters as if they were contained in a probe."""
    # The artifact isn't actually used for anything, it's just required to
    # initialize handlers.
    probe = rdfvalue.Probe(artifact="Data", filters=filt_defs)
    return probe.filters

  def testValidateFilters(self):
    self.assertEquals(2, len(self.GetFilters(self.ok)))
    self.assertRaises(filters.DefinitionError, self.GetFilters, self.bad)

  def testNoOpHandler(self):
    h = filters.GetHandler("PASSTHROUGH")
    handler = h("Data", filters=self.GetFilters(self.ok))
    self.assertItemsEqual(self.all, handler.Parse(self.all))

  def testParallelHandler(self):
    h = filters.GetHandler("PARALLEL")
    handler = h("Data", filters=self.GetFilters(self.ok))
    self.assertItemsEqual(self.parallel, handler.Parse(self.all))

  def testSerialHandler(self):
    h = filters.GetHandler("SERIAL")
    handler = h("Data", filters=self.GetFilters(self.ok))
    self.assertItemsEqual(self.serial, handler.Parse(self.all))


def main(argv):
  test_lib.main(argv)

if __name__ == "__main__":
  flags.StartMain(main)
