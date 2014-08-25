#!/usr/bin/env python
"""Test AFF4 RDFValues."""



import re

from grr.lib import rdfvalue
from grr.lib import type_info
from grr.lib import utils

from grr.lib.rdfvalues import test_base


class AFF4ObjectLabelTest(test_base.RDFValueTestCase):
  """Test AFF4ObjectLabel."""

  rdfvalue_class = rdfvalue.AFF4ObjectLabel

  def GenerateSample(self, number=0):
    return rdfvalue.AFF4ObjectLabel(
        name="label%d" % number, owner="test",
        timestamp=rdfvalue.RDFDatetime().FromSecondsFromEpoch(42))

  def testAlphanumericCharactersAreAllowed(self):
    rdfvalue.AFF4ObjectLabel(name="label42", owner="test")

  def testDotIsAllowed(self):
    rdfvalue.AFF4ObjectLabel(name="label.42", owner="test")

  def testColonIsAllowed(self):
    rdfvalue.AFF4ObjectLabel(name="label.42:1", owner="test")

  def testForwardSlashIsAllowed(self):
    rdfvalue.AFF4ObjectLabel(name="b/label.42:1", owner="test")

  def testEmptyStringNameIsNotAllowed(self):
    self.assertRaises(type_info.TypeValueError, rdfvalue.AFF4ObjectLabel,
                      name="", owner="test")

  def testLabelWithoutAnOwnerIsNotAllowed(self):
    self.assertRaises(type_info.TypeValueError, rdfvalue.AFF4ObjectLabel,
                      name="foo")

  def testLabelWithEmptyOwnerIsNotAllowed(self):
    self.assertRaises(type_info.TypeValueError, rdfvalue.AFF4ObjectLabel,
                      name="foo", owner="")

  def testNonAlphanumericsDotsColonOrForwardSlashAreNotAllowed(self):
    self.assertRaises(type_info.TypeValueError, rdfvalue.AFF4ObjectLabel,
                      name="label,42")
    self.assertRaises(type_info.TypeValueError, rdfvalue.AFF4ObjectLabel,
                      name="label[42")
    self.assertRaises(type_info.TypeValueError, rdfvalue.AFF4ObjectLabel,
                      name="label]42")
    self.assertRaises(type_info.TypeValueError, rdfvalue.AFF4ObjectLabel,
                      name="label\\42")


class AFF4ObjectLabelsListTest(test_base.RDFValueTestCase):
  """Test AFF4ObjectLabelsList."""

  rdfvalue_class = rdfvalue.AFF4ObjectLabelsList

  def GenerateSample(self, number=0):
    label1 = rdfvalue.AFF4ObjectLabel(
        name="foo_%d" % number, owner="test",
        timestamp=rdfvalue.RDFDatetime().FromSecondsFromEpoch(42))

    label2 = rdfvalue.AFF4ObjectLabel(
        name="bar_%d" % number, owner="test",
        timestamp=rdfvalue.RDFDatetime().FromSecondsFromEpoch(42))

    return rdfvalue.AFF4ObjectLabelsList(labels=[label1, label2])

  def testAddLabelAddsLabelWithSameNameButDifferentOwner(self):
    labels_list = rdfvalue.AFF4ObjectLabelsList()

    labels_list.AddLabel(rdfvalue.AFF4ObjectLabel(name="foo",
                                                  owner="test"))
    self.assertEqual(len(labels_list.labels), 1)

    labels_list.AddLabel(rdfvalue.AFF4ObjectLabel(name="foo",
                                                  owner="GRR"))
    self.assertEqual(len(labels_list.labels), 2)

  def testAddLabelDoesNotAddLabelWithSameNameAndOwner(self):
    labels_list = rdfvalue.AFF4ObjectLabelsList()

    labels_list.AddLabel(rdfvalue.AFF4ObjectLabel(name="foo",
                                                  owner="test"))
    self.assertEqual(len(labels_list.labels), 1)

    labels_list.AddLabel(rdfvalue.AFF4ObjectLabel(name="foo",
                                                  owner="test"))
    self.assertEqual(len(labels_list.labels), 1)

  def testStringifiedValueIsLabelsNamesWithoutOwners(self):
    labels_list = rdfvalue.AFF4ObjectLabelsList()

    labels_list.AddLabel(rdfvalue.AFF4ObjectLabel(name="bar",
                                                  owner="GRR"))
    labels_list.AddLabel(rdfvalue.AFF4ObjectLabel(name="foo",
                                                  owner="test"))

    self.assertEqual(utils.SmartStr(labels_list), "bar,foo")

  def testStringifiedRepresentationIsSorted(self):
    labels_list = rdfvalue.AFF4ObjectLabelsList()

    labels_list.AddLabel(rdfvalue.AFF4ObjectLabel(name="foo",
                                                  owner="GRR"))
    labels_list.AddLabel(rdfvalue.AFF4ObjectLabel(name="bar",
                                                  owner="test"))

    self.assertEqual(utils.SmartStr(labels_list), "bar,foo")

  def testStringifiedValueDoesNotHaveDuplicates(self):
    labels_list = rdfvalue.AFF4ObjectLabelsList()

    labels_list.AddLabel(rdfvalue.AFF4ObjectLabel(name="foo",
                                                  owner="GRR"))
    labels_list.AddLabel(rdfvalue.AFF4ObjectLabel(name="bar",
                                                  owner="GRR"))
    labels_list.AddLabel(rdfvalue.AFF4ObjectLabel(name="foo",
                                                  owner="test"))

    self.assertEqual(utils.SmartStr(labels_list), "bar,foo")

  def testRegexForStringifiedValueMatchMatchesLabelsInList(self):
    labels_list = rdfvalue.AFF4ObjectLabelsList()

    labels_list.AddLabel(rdfvalue.AFF4ObjectLabel(name="ein",
                                                  owner="GRR"))
    labels_list.AddLabel(rdfvalue.AFF4ObjectLabel(name="zwei",
                                                  owner="test"))
    labels_list.AddLabel(rdfvalue.AFF4ObjectLabel(name="drei",
                                                  owner="GRR"))
    labels_list.AddLabel(rdfvalue.AFF4ObjectLabel(name="vier",
                                                  owner="test"))

    self.assertTrue(re.match(
        rdfvalue.AFF4ObjectLabelsList.RegexForStringifiedValueMatch("ein"),
        str(labels_list)))
    self.assertTrue(re.match(
        rdfvalue.AFF4ObjectLabelsList.RegexForStringifiedValueMatch("zwei"),
        str(labels_list)))
    self.assertTrue(re.match(
        rdfvalue.AFF4ObjectLabelsList.RegexForStringifiedValueMatch("drei"),
        str(labels_list)))
    self.assertTrue(re.match(
        rdfvalue.AFF4ObjectLabelsList.RegexForStringifiedValueMatch("vier"),
        str(labels_list)))

  def testRegexForStringifiedValueDoesNotMatchLabelsNotInList(self):
    labels_list = rdfvalue.AFF4ObjectLabelsList()

    labels_list.AddLabel(rdfvalue.AFF4ObjectLabel(name="ein",
                                                  owner="GRR"))
    labels_list.AddLabel(rdfvalue.AFF4ObjectLabel(name="zwei",
                                                  owner="test"))
    self.assertFalse(re.match(
        rdfvalue.AFF4ObjectLabelsList.RegexForStringifiedValueMatch("e"),
        str(labels_list)))
    self.assertFalse(re.match(
        rdfvalue.AFF4ObjectLabelsList.RegexForStringifiedValueMatch("in"),
        str(labels_list)))
    self.assertFalse(re.match(
        rdfvalue.AFF4ObjectLabelsList.RegexForStringifiedValueMatch("a.zwer"),
        str(labels_list)))
    self.assertFalse(re.match(
        rdfvalue.AFF4ObjectLabelsList.RegexForStringifiedValueMatch("ein."),
        str(labels_list)))
