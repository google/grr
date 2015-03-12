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


class BaseFilterTests(test_lib.GRRBaseTest):
  """Test objectfilter methods and operations."""

  def testIterate(self):
    filt = filters.Filter()
    result = list(filt._Iterate("basestr"))
    self.assertEqual(["basestr"], result)

  def testValidate(self):
    filt = filters.Filter()
    self.assertRaises(NotImplementedError, filt.Validate, "anything")

  def testParse(self):
    filt = filters.Filter()
    self.assertRaises(NotImplementedError, filt.Parse, None, "do nothing")


class AttrFilterTests(test_lib.GRRBaseTest):
  """Test objectfilter methods and operations."""

  def testValidate(self):
    filt = filters.AttrFilter()
    self.assertRaises(filters.DefinitionError, filt.Validate, " ")
    self.assertFalse(filt.Validate("cfg1"))
    self.assertFalse(filt.Validate("cfg1 cfg1.test1"))

  def testParse(self):
    filt = filters.AttrFilter()

    hit = rdfvalue.Config(test1="1", test2=2, test3=[3, 4])
    miss = rdfvalue.Config(test1="5", test2=6, test3=[7, 8])
    metacfg = rdfvalue.Config(hit=hit, miss=miss)

    result = list(filt.Parse(hit, "test1 test2"))
    self.assertEqual(2, len(result))
    self.assertEqual("test1", result[0].k)
    self.assertEqual("1", result[0].v)
    self.assertEqual("test2", result[1].k)
    self.assertEqual(2, result[1].v)

    result = list(filt.Parse(metacfg, "hit.test3"))
    self.assertEqual(1, len(result))
    self.assertEqual("hit.test3", result[0].k)
    self.assertEqual([3, 4], result[0].v)


class ItemFilterTests(test_lib.GRRBaseTest):
  """Test itemfilter methods and operations."""

  def testParse(self):
    filt = filters.ItemFilter()

    cfg = rdfvalue.Config(test1="1", test2=[2, 3])

    result = list(filt.Parse(cfg, "test1 is '1'"))
    self.assertEqual(1, len(result))
    self.assertEqual("test1", result[0].k)
    self.assertEqual("1", result[0].v)

    result = list(filt.Parse(cfg, "test1 is '2'"))
    self.assertFalse(result)

    result = list(filt.Parse(cfg, "test2 contains 3"))
    self.assertEqual(1, len(result))
    self.assertEqual("test2", result[0].k)
    self.assertEqual([2, 3], result[0].v)

    # Ensure this works on other RDF types, not just Configs.
    cfg = rdfvalue.Filesystem(device="/dev/sda1", mount_point="/root")
    result = list(filt.Parse(cfg, "mount_point is '/root'"))
    self.assertEqual(1, len(result))
    self.assertEqual("mount_point", result[0].k)
    self.assertEqual("/root", result[0].v)


class ObjectFilterTests(test_lib.GRRBaseTest):
  """Test objectfilter methods and operations."""

  def testValidate(self):
    filt = filters.ObjectFilter()
    self.assertRaises(filters.DefinitionError, filt.Validate, "bad term")
    self.assertFalse(filt.Validate("test is 'ok'"))

  def testParse(self):
    filt = filters.ObjectFilter()

    cfg = rdfvalue.Config(test="ok")
    results = list(filt.Parse(cfg, "test is 'ok'"))
    self.assertEqual([cfg], results)

    cfg = rdfvalue.Config(test="miss")
    results = list(filt.Parse(cfg, "test is 'ok'"))
    self.assertEqual([], results)


class RDFFilterTests(test_lib.GRRBaseTest):
  """Test objectfilter methods and operations."""

  def testValidate(self):
    filt = filters.RDFFilter()
    self.assertFalse(filt.Validate("KnowledgeBase,Config"))
    self.assertRaises(filters.DefinitionError, filt.Validate,
                      "KnowledgeBase,Nonexistent")

  def testParse(self):
    filt = filters.RDFFilter()
    cfg = rdfvalue.Config()
    results = list(filt.Parse(cfg, "KnowledgeBase"))
    self.assertFalse(results)
    results = list(filt.Parse(cfg, "KnowledgeBase,Config"))
    self.assertItemsEqual([cfg], results)


class FilterRegistryTests(test_lib.GRRBaseTest):
  """Test filter methods and operations."""

  def testFilterRegistry(self):
    filters.Filter.filters = {}

    filt = filters.Filter.GetFilter("Filter")
    # It should be the right type of filter.
    # And should be in the registry already.
    self.assertIsInstance(filt, filters.Filter)
    self.assertEqual(filt, filters.Filter.GetFilter("Filter"))

    filt = filters.Filter.GetFilter("ObjectFilter")
    self.assertIsInstance(filt, filters.ObjectFilter)
    self.assertEqual(filt, filters.Filter.GetFilter("ObjectFilter"))

    filt = filters.Filter.GetFilter("RDFFilter")
    self.assertIsInstance(filt, filters.RDFFilter)
    self.assertEqual(filt, filters.Filter.GetFilter("RDFFilter"))

    filters.Filter.filters = {}
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

  def GetFilters(self, filt_defs):
    """Initialize one or more filters as if they were contained in a probe."""
    # The artifact isn't actually used for anything, it's just required to
    # initialize handlers.
    probe = rdfvalue.Probe(artifact="Data", filters=filt_defs)
    return probe.filters

  def testValidateFilters(self):
    self.assertEquals(2, len(self.GetFilters(self.ok)))
    self.assertRaises(filters.DefinitionError, self.GetFilters, self.bad)

  def testBaseHandler(self):
    # Handler needs an artifact.
    self.assertRaises(filters.DefinitionError, filters.BaseHandler)
    h = filters.BaseHandler("STUB")
    self.assertRaises(NotImplementedError, h.Parse, "STUB")

  def testNoOpHandler(self):
    h = filters.GetHandler("PASSTHROUGH")
    handler = h("Data", filters=self.GetFilters(self.ok))
    self.assertItemsEqual(self.all, handler.Parse(self.all))

  def testParallelHandler(self):
    h = filters.GetHandler("PARALLEL")
    # Without filters.
    handler = h("Data", filters=[])
    self.assertItemsEqual(self.all, handler.Parse(self.all))
    # With filters.
    handler = h("Data", filters=self.GetFilters(self.ok))
    expected = [Sample(0, 0), Sample(0, 1), Sample(1, 0)]
    self.assertItemsEqual(expected, handler.Parse(self.all))

  def testSerialHandler(self):
    h = filters.GetHandler("SERIAL")
    # Without filters.
    handler = h("Data", filters=[])
    self.assertItemsEqual(self.all, handler.Parse(self.all))
    # With filters.
    handler = h("Data", filters=self.GetFilters(self.ok))
    expected = [Sample(0, 0)]
    self.assertItemsEqual(expected, handler.Parse(self.all))


def main(argv):
  test_lib.main(argv)

if __name__ == "__main__":
  flags.StartMain(main)
