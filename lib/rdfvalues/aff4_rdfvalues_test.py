#!/usr/bin/env python
"""Test AFF4 RDFValues."""



import re

from grr.lib import rdfvalue
from grr.lib import type_info
from grr.lib import utils

from grr.lib.rdfvalues import aff4_rdfvalues
from grr.lib.rdfvalues import test_base


class AFF4ObjectLabelTest(test_base.RDFValueTestCase):
  """Test AFF4ObjectLabel."""

  rdfvalue_class = aff4_rdfvalues.AFF4ObjectLabel

  def GenerateSample(self, number=0):
    return aff4_rdfvalues.AFF4ObjectLabel(
        name="label%d" % number,
        owner="test",
        timestamp=rdfvalue.RDFDatetime().FromSecondsFromEpoch(42))

  def testAlphanumericCharactersAreAllowed(self):
    aff4_rdfvalues.AFF4ObjectLabel(name="label42", owner="test")

  def testDotIsAllowed(self):
    aff4_rdfvalues.AFF4ObjectLabel(name="label.42", owner="test")

  def testColonIsAllowed(self):
    aff4_rdfvalues.AFF4ObjectLabel(name="label.42:1", owner="test")

  def testForwardSlashIsAllowed(self):
    aff4_rdfvalues.AFF4ObjectLabel(name="b/label.42:1", owner="test")

  def testEmptyStringNameIsNotAllowed(self):
    self.assertRaises(type_info.TypeValueError, aff4_rdfvalues.AFF4ObjectLabel,
                      name="",
                      owner="test")

  def testNonAlphanumericsDotsColonOrForwardSlashAreNotAllowed(self):
    self.assertRaises(type_info.TypeValueError, aff4_rdfvalues.AFF4ObjectLabel,
                      name="label,42")
    self.assertRaises(type_info.TypeValueError, aff4_rdfvalues.AFF4ObjectLabel,
                      name="label[42")
    self.assertRaises(type_info.TypeValueError, aff4_rdfvalues.AFF4ObjectLabel,
                      name="label]42")
    self.assertRaises(type_info.TypeValueError, aff4_rdfvalues.AFF4ObjectLabel,
                      name="label\\42")


class AFF4ObjectLabelsListTest(test_base.RDFValueTestCase):
  """Test AFF4ObjectLabelsList."""

  rdfvalue_class = aff4_rdfvalues.AFF4ObjectLabelsList

  def GenerateSample(self, number=0):
    label1 = aff4_rdfvalues.AFF4ObjectLabel(
        name="foo_%d" % number,
        owner="test",
        timestamp=rdfvalue.RDFDatetime().FromSecondsFromEpoch(42))

    label2 = aff4_rdfvalues.AFF4ObjectLabel(
        name="bar_%d" % number,
        owner="test",
        timestamp=rdfvalue.RDFDatetime().FromSecondsFromEpoch(42))

    return aff4_rdfvalues.AFF4ObjectLabelsList(labels=[label1, label2])

  def testAddLabelAddsLabelWithSameNameButDifferentOwner(self):
    labels_list = aff4_rdfvalues.AFF4ObjectLabelsList()

    labels_list.AddLabel(aff4_rdfvalues.AFF4ObjectLabel(name="foo",
                                                        owner="test"))
    self.assertEqual(len(labels_list.labels), 1)

    labels_list.AddLabel(aff4_rdfvalues.AFF4ObjectLabel(name="foo",
                                                        owner="GRR"))
    self.assertEqual(len(labels_list.labels), 2)

  def testAddLabelDoesNotAddLabelWithSameNameAndOwner(self):
    labels_list = aff4_rdfvalues.AFF4ObjectLabelsList()

    labels_list.AddLabel(aff4_rdfvalues.AFF4ObjectLabel(name="foo",
                                                        owner="test"))
    self.assertEqual(len(labels_list.labels), 1)

    labels_list.AddLabel(aff4_rdfvalues.AFF4ObjectLabel(name="foo",
                                                        owner="test"))
    self.assertEqual(len(labels_list.labels), 1)

  def testStringifiedValueIsLabelsNamesWithoutOwners(self):
    labels_list = aff4_rdfvalues.AFF4ObjectLabelsList()

    labels_list.AddLabel(aff4_rdfvalues.AFF4ObjectLabel(name="bar",
                                                        owner="GRR"))
    labels_list.AddLabel(aff4_rdfvalues.AFF4ObjectLabel(name="foo",
                                                        owner="test"))

    self.assertEqual(utils.SmartStr(labels_list), "bar,foo")

  def testStringifiedRepresentationIsSorted(self):
    labels_list = aff4_rdfvalues.AFF4ObjectLabelsList()

    labels_list.AddLabel(aff4_rdfvalues.AFF4ObjectLabel(name="foo",
                                                        owner="GRR"))
    labels_list.AddLabel(aff4_rdfvalues.AFF4ObjectLabel(name="bar",
                                                        owner="test"))

    self.assertEqual(utils.SmartStr(labels_list), "bar,foo")

  def testStringifiedValueDoesNotHaveDuplicates(self):
    labels_list = aff4_rdfvalues.AFF4ObjectLabelsList()

    labels_list.AddLabel(aff4_rdfvalues.AFF4ObjectLabel(name="foo",
                                                        owner="GRR"))
    labels_list.AddLabel(aff4_rdfvalues.AFF4ObjectLabel(name="bar",
                                                        owner="GRR"))
    labels_list.AddLabel(aff4_rdfvalues.AFF4ObjectLabel(name="foo",
                                                        owner="test"))

    self.assertEqual(utils.SmartStr(labels_list), "bar,foo")

  def testRegexForStringifiedValueMatchMatchesLabelsInList(self):
    labels_list = aff4_rdfvalues.AFF4ObjectLabelsList()

    labels_list.AddLabel(aff4_rdfvalues.AFF4ObjectLabel(name="ein",
                                                        owner="GRR"))
    labels_list.AddLabel(aff4_rdfvalues.AFF4ObjectLabel(name="zwei",
                                                        owner="test"))
    labels_list.AddLabel(aff4_rdfvalues.AFF4ObjectLabel(name="drei",
                                                        owner="GRR"))
    labels_list.AddLabel(aff4_rdfvalues.AFF4ObjectLabel(name="vier",
                                                        owner="test"))

    self.assertTrue(re.match(
        aff4_rdfvalues.AFF4ObjectLabelsList.RegexForStringifiedValueMatch(
            "ein"), str(labels_list)))
    self.assertTrue(re.match(
        aff4_rdfvalues.AFF4ObjectLabelsList.RegexForStringifiedValueMatch(
            "zwei"), str(labels_list)))
    self.assertTrue(re.match(
        aff4_rdfvalues.AFF4ObjectLabelsList.RegexForStringifiedValueMatch(
            "drei"), str(labels_list)))
    self.assertTrue(re.match(
        aff4_rdfvalues.AFF4ObjectLabelsList.RegexForStringifiedValueMatch(
            "vier"), str(labels_list)))

  def testRegexForStringifiedValueDoesNotMatchLabelsNotInList(self):
    labels_list = aff4_rdfvalues.AFF4ObjectLabelsList()

    labels_list.AddLabel(aff4_rdfvalues.AFF4ObjectLabel(name="ein",
                                                        owner="GRR"))
    labels_list.AddLabel(aff4_rdfvalues.AFF4ObjectLabel(name="zwei",
                                                        owner="test"))
    self.assertFalse(re.match(
        aff4_rdfvalues.AFF4ObjectLabelsList.RegexForStringifiedValueMatch("e"),
        str(labels_list)))
    self.assertFalse(re.match(
        aff4_rdfvalues.AFF4ObjectLabelsList.RegexForStringifiedValueMatch("in"),
        str(labels_list)))
    self.assertFalse(re.match(
        aff4_rdfvalues.AFF4ObjectLabelsList.RegexForStringifiedValueMatch(
            "a.zwer"), str(labels_list)))
    self.assertFalse(re.match(
        aff4_rdfvalues.AFF4ObjectLabelsList.RegexForStringifiedValueMatch(
            "ein."), str(labels_list)))

  def testGetSortedLabelSet(self):
    labels_list = aff4_rdfvalues.AFF4ObjectLabelsList()

    labels_list.AddLabel(aff4_rdfvalues.AFF4ObjectLabel(name="foo",
                                                        owner="test"))
    labels_list.AddLabel(aff4_rdfvalues.AFF4ObjectLabel(name="foo2",
                                                        owner="test2"))
    labels_list.AddLabel(aff4_rdfvalues.AFF4ObjectLabel(name="foo3",
                                                        owner="test2"))

    self.assertItemsEqual(labels_list.GetLabelNames(), ["foo", "foo2", "foo3"])
    self.assertItemsEqual(labels_list.GetLabelNames(owner="test2"), ["foo2",
                                                                     "foo3"])
    self.assertEqual(labels_list.GetLabelNames(owner="test4"), [])
