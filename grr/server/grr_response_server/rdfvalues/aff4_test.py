#!/usr/bin/env python
"""Test AFF4 RDFValues."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib import flags
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import type_info
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import test_base as rdf_test_base

from grr_response_server.rdfvalues import aff4 as rdf_aff4
from grr.test_lib import test_lib


class AFF4ObjectLabelTest(rdf_test_base.RDFValueTestMixin,
                          test_lib.GRRBaseTest):
  """Test AFF4ObjectLabel."""

  rdfvalue_class = rdf_aff4.AFF4ObjectLabel

  def GenerateSample(self, number=0):
    return rdf_aff4.AFF4ObjectLabel(
        name="label%d" % number,
        owner="test",
        timestamp=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(42))

  def testAlphanumericCharactersAreAllowed(self):
    rdf_aff4.AFF4ObjectLabel(name="label42", owner="test")

  def testDotIsAllowed(self):
    rdf_aff4.AFF4ObjectLabel(name="label.42", owner="test")

  def testColonIsAllowed(self):
    rdf_aff4.AFF4ObjectLabel(name="label.42:1", owner="test")

  def testForwardSlashIsAllowed(self):
    rdf_aff4.AFF4ObjectLabel(name="b/label.42:1", owner="test")

  def testEmptyStringNameIsNotAllowed(self):
    self.assertRaises(
        type_info.TypeValueError,
        rdf_aff4.AFF4ObjectLabel,
        name="",
        owner="test")

  def testNonAlphanumericsDotsColonOrForwardSlashAreNotAllowed(self):
    self.assertRaises(
        type_info.TypeValueError, rdf_aff4.AFF4ObjectLabel, name="label,42")
    self.assertRaises(
        type_info.TypeValueError, rdf_aff4.AFF4ObjectLabel, name="label[42")
    self.assertRaises(
        type_info.TypeValueError, rdf_aff4.AFF4ObjectLabel, name="label]42")
    self.assertRaises(
        type_info.TypeValueError, rdf_aff4.AFF4ObjectLabel, name="label\\42")


class AFF4ObjectLabelsListTest(rdf_test_base.RDFValueTestMixin,
                               test_lib.GRRBaseTest):
  """Test AFF4ObjectLabelsList."""

  rdfvalue_class = rdf_aff4.AFF4ObjectLabelsList

  def GenerateSample(self, number=0):
    label1 = rdf_aff4.AFF4ObjectLabel(
        name="foo_%d" % number,
        owner="test",
        timestamp=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(42))

    label2 = rdf_aff4.AFF4ObjectLabel(
        name="bar_%d" % number,
        owner="test",
        timestamp=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(42))

    return rdf_aff4.AFF4ObjectLabelsList(labels=[label1, label2])

  def testAddLabelAddsLabelWithSameNameButDifferentOwner(self):
    labels_list = rdf_aff4.AFF4ObjectLabelsList()

    labels_list.AddLabel(rdf_aff4.AFF4ObjectLabel(name="foo", owner="test"))
    self.assertLen(labels_list.labels, 1)

    labels_list.AddLabel(rdf_aff4.AFF4ObjectLabel(name="foo", owner="GRR"))
    self.assertLen(labels_list.labels, 2)

  def testAddLabelDoesNotAddLabelWithSameNameAndOwner(self):
    labels_list = rdf_aff4.AFF4ObjectLabelsList()

    labels_list.AddLabel(rdf_aff4.AFF4ObjectLabel(name="foo", owner="test"))
    self.assertLen(labels_list.labels, 1)

    labels_list.AddLabel(rdf_aff4.AFF4ObjectLabel(name="foo", owner="test"))
    self.assertLen(labels_list.labels, 1)

  def testStringifiedValueIsLabelsNamesWithoutOwners(self):
    labels_list = rdf_aff4.AFF4ObjectLabelsList()

    labels_list.AddLabel(rdf_aff4.AFF4ObjectLabel(name="bar", owner="GRR"))
    labels_list.AddLabel(rdf_aff4.AFF4ObjectLabel(name="foo", owner="test"))

    self.assertEqual(utils.SmartStr(labels_list), "bar,foo")

  def testStringifiedRepresentationIsSorted(self):
    labels_list = rdf_aff4.AFF4ObjectLabelsList()

    labels_list.AddLabel(rdf_aff4.AFF4ObjectLabel(name="foo", owner="GRR"))
    labels_list.AddLabel(rdf_aff4.AFF4ObjectLabel(name="bar", owner="test"))

    self.assertEqual(utils.SmartStr(labels_list), "bar,foo")

  def testStringifiedValueDoesNotHaveDuplicates(self):
    labels_list = rdf_aff4.AFF4ObjectLabelsList()

    labels_list.AddLabel(rdf_aff4.AFF4ObjectLabel(name="foo", owner="GRR"))
    labels_list.AddLabel(rdf_aff4.AFF4ObjectLabel(name="bar", owner="GRR"))
    labels_list.AddLabel(rdf_aff4.AFF4ObjectLabel(name="foo", owner="test"))

    self.assertEqual(utils.SmartStr(labels_list), "bar,foo")

  def testRegexForStringifiedValueMatchMatchesLabelsInList(self):
    labels_list = rdf_aff4.AFF4ObjectLabelsList()

    labels_list.AddLabel(rdf_aff4.AFF4ObjectLabel(name="ein", owner="GRR"))
    labels_list.AddLabel(rdf_aff4.AFF4ObjectLabel(name="zwei", owner="test"))
    labels_list.AddLabel(rdf_aff4.AFF4ObjectLabel(name="drei", owner="GRR"))
    labels_list.AddLabel(rdf_aff4.AFF4ObjectLabel(name="vier", owner="test"))

    self.assertRegexpMatches(
        str(labels_list),
        rdf_aff4.AFF4ObjectLabelsList.RegexForStringifiedValueMatch("ein"))
    self.assertRegexpMatches(
        str(labels_list),
        rdf_aff4.AFF4ObjectLabelsList.RegexForStringifiedValueMatch("zwei"))
    self.assertRegexpMatches(
        str(labels_list),
        rdf_aff4.AFF4ObjectLabelsList.RegexForStringifiedValueMatch("drei"))
    self.assertRegexpMatches(
        str(labels_list),
        rdf_aff4.AFF4ObjectLabelsList.RegexForStringifiedValueMatch("vier"))

  def testRegexForStringifiedValueDoesNotMatchLabelsNotInList(self):
    labels_list = rdf_aff4.AFF4ObjectLabelsList()

    labels_list.AddLabel(rdf_aff4.AFF4ObjectLabel(name="ein", owner="GRR"))
    labels_list.AddLabel(rdf_aff4.AFF4ObjectLabel(name="zwei", owner="test"))
    self.assertNotRegexpMatches(
        str(labels_list),
        rdf_aff4.AFF4ObjectLabelsList.RegexForStringifiedValueMatch("e"))
    self.assertNotRegexpMatches(
        str(labels_list),
        rdf_aff4.AFF4ObjectLabelsList.RegexForStringifiedValueMatch("in"))
    self.assertNotRegexpMatches(
        str(labels_list),
        rdf_aff4.AFF4ObjectLabelsList.RegexForStringifiedValueMatch("a.zwer"))
    self.assertNotRegexpMatches(
        str(labels_list),
        rdf_aff4.AFF4ObjectLabelsList.RegexForStringifiedValueMatch("ein."))

  def testGetSortedLabelSet(self):
    labels_list = rdf_aff4.AFF4ObjectLabelsList()

    labels_list.AddLabel(rdf_aff4.AFF4ObjectLabel(name="foo", owner="test"))
    labels_list.AddLabel(rdf_aff4.AFF4ObjectLabel(name="foo2", owner="test2"))
    labels_list.AddLabel(rdf_aff4.AFF4ObjectLabel(name="foo3", owner="test2"))

    self.assertCountEqual(labels_list.GetLabelNames(), ["foo", "foo2", "foo3"])
    self.assertCountEqual(
        labels_list.GetLabelNames(owner="test2"), ["foo2", "foo3"])
    self.assertEqual(labels_list.GetLabelNames(owner="test4"), [])


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
