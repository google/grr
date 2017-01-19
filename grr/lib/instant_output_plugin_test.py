#!/usr/bin/env python
"""Tests for grr.lib.output_plugin."""


from grr.lib import aff4
from grr.lib import export
from grr.lib import flags
from grr.lib import instant_output_plugin
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib.aff4_objects import multi_type_collection
from grr.lib.output_plugins import test_plugins


class ApplyPluginToMultiTypeCollectionTest(test_lib.GRRBaseTest):
  """Tests for ApplyPluginToMultiTypeCollection() function."""

  def setUp(self):
    super(ApplyPluginToMultiTypeCollectionTest, self).setUp()
    self.plugin = test_plugins.TestInstantOutputPlugin(
        source_urn=rdfvalue.RDFURN("aff4:/foo/bar"), token=self.token)

    self.collection = aff4.FACTORY.Create(
        "aff4:/mt_collection/testAddScan",
        multi_type_collection.MultiTypeCollection,
        token=self.token)

  def ProcessPlugin(self):
    return list(
        instant_output_plugin.ApplyPluginToMultiTypeCollection(self.plugin,
                                                               self.collection))

  def testCorrectlyExportsSingleValue(self):
    self.collection.Add(rdfvalue.RDFString("foo"))

    chunks = self.ProcessPlugin()

    self.assertListEqual(chunks, [
        "Start: aff4:/foo/bar",
        "Values of type: RDFString",
        "First pass: foo",
        "Second pass: foo",
        "Finish: aff4:/foo/bar"
    ])  # pyformat: disable

  def testCorrectlyExportsTwoValuesOfTheSameType(self):
    self.collection.Add(rdfvalue.RDFString("foo"))
    self.collection.Add(rdfvalue.RDFString("bar"))

    chunks = self.ProcessPlugin()

    self.assertListEqual(chunks, [
        "Start: aff4:/foo/bar",
        "Values of type: RDFString",
        "First pass: foo",
        "First pass: bar",
        "Second pass: foo",
        "Second pass: bar",
        "Finish: aff4:/foo/bar"
    ])  # pyformat: disable

  def testCorrectlyExportsFourValuesOfTwoDifferentTypes(self):
    self.collection.Add(rdfvalue.RDFString("foo"))
    self.collection.Add(rdfvalue.RDFInteger(42))
    self.collection.Add(rdfvalue.RDFString("bar"))
    self.collection.Add(rdfvalue.RDFInteger(43))

    chunks = self.ProcessPlugin()

    self.assertListEqual(chunks, [
        "Start: aff4:/foo/bar",
        "Values of type: RDFInteger",
        "First pass: 42",
        "First pass: 43",
        "Second pass: 42",
        "Second pass: 43",
        "Values of type: RDFString",
        "First pass: foo",
        "First pass: bar",
        "Second pass: foo",
        "Second pass: bar",
        "Finish: aff4:/foo/bar"
    ])  # pyformat: disable


class DummySrcValue1(rdfvalue.RDFString):
  pass


class DummySrcValue2(rdfvalue.RDFString):
  pass


class DummyOutValue1(rdfvalue.RDFString):
  pass


class DummyOutValue2(rdfvalue.RDFString):
  pass


class TestConverter1(export.ExportConverter):
  input_rdf_type = "DummySrcValue1"

  def Convert(self, metadata, value, token=None):
    _ = metadata
    _ = token
    return [DummyOutValue1("exp-" + str(value))]


class TestConverter2(export.ExportConverter):
  input_rdf_type = "DummySrcValue2"

  def Convert(self, metadata, value, token=None):
    _ = metadata
    _ = token
    return [
        DummyOutValue1("exp1-" + str(value)),
        DummyOutValue2("exp2-" + str(value))
    ]


class InstantOutputPluginWithExportConversionTest(
    test_plugins.InstantOutputPluginTestBase):
  """Tests for InstantOutputPluginWithExportConversion."""

  plugin_cls = test_plugins.TestInstantOutputPluginWithExportConverstion

  def ProcessValuesToLines(self, values_by_cls):
    fd_name = self.ProcessValues(values_by_cls)
    with open(fd_name, "r") as fd:
      return fd.read().split("\n")

  def testWorksCorrectlyWithOneSourceValueAndOneExportedValue(self):
    lines = self.ProcessValuesToLines({DummySrcValue1: DummySrcValue1("foo")})
    self.assertListEqual(lines, [
        "Start",
        "Original: DummySrcValue1",
        "Exported value: exp-foo",
        "Finish"
    ])  # pyformat: disable

  def testWorksCorrectlyWithOneSourceValueAndTwoExportedValues(self):
    lines = self.ProcessValuesToLines({DummySrcValue2: DummySrcValue2("foo")})
    self.assertListEqual(lines, [
        "Start",
        "Original: DummySrcValue2",
        "Exported value: exp1-foo",
        "Original: DummySrcValue2",
        "Exported value: exp2-foo",
        "Finish"
    ])  # pyformat: disable

  def testWorksCorrectlyWithTwoSourceValueAndTwoExportedValuesEach(self):
    lines = self.ProcessValuesToLines({
        DummySrcValue2: [DummySrcValue2("foo"), DummySrcValue2("bar")]
    })
    self.assertListEqual(lines, [
        "Start",
        "Original: DummySrcValue2",
        "Exported value: exp1-foo",
        "Exported value: exp1-bar",
        "Original: DummySrcValue2",
        "Exported value: exp2-foo",
        "Exported value: exp2-bar",
        "Finish"
    ])  # pyformat: disable

  def testWorksCorrectlyWithTwoDifferentTypesOfSourceValues(self):
    lines = self.ProcessValuesToLines({
        DummySrcValue1: [DummySrcValue1("foo")],
        DummySrcValue2: [DummySrcValue2("bar")],
    })
    self.assertListEqual(lines, [
        "Start",
        "Original: DummySrcValue1",
        "Exported value: exp-foo",
        "Original: DummySrcValue2",
        "Exported value: exp1-bar",
        "Original: DummySrcValue2",
        "Exported value: exp2-bar",
        "Finish"
    ])  # pyformat: disable


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
