#!/usr/bin/env python
"""Tests for grr.lib.output_plugin."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


from grr_response_core.lib import flags
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_server import data_store
from grr_response_server import export
from grr_response_server import instant_output_plugin
from grr_response_server import multi_type_collection
from grr_response_server.output_plugins import test_plugins
from grr.test_lib import db_test_lib
from grr.test_lib import test_lib


@db_test_lib.DualDBTest
class ApplyPluginToMultiTypeCollectionTest(test_lib.GRRBaseTest):
  """Tests for ApplyPluginToMultiTypeCollection() function."""

  def setUp(self):
    super(ApplyPluginToMultiTypeCollectionTest, self).setUp()
    self.plugin = test_plugins.TestInstantOutputPlugin(
        source_urn=rdfvalue.RDFURN("aff4:/foo/bar"), token=self.token)

    self.client_id = self.SetupClient(0)
    self.pool = data_store.DB.GetMutationPool()
    self.collection = multi_type_collection.MultiTypeCollection(
        rdfvalue.RDFURN("aff4:/mt_collection/testAddScan"))

  def ProcessPlugin(self, source_urn=None):
    return list(
        instant_output_plugin.ApplyPluginToMultiTypeCollection(
            self.plugin, self.collection, source_urn=source_urn))

  def testCorrectlyExportsSingleValue(self):
    with self.pool:
      self.collection.Add(
          rdf_flows.GrrMessage(
              payload=rdfvalue.RDFString("foo"), source=self.client_id),
          mutation_pool=self.pool)

    chunks = self.ProcessPlugin()

    self.assertListEqual(chunks, [
        "Start: aff4:/foo/bar",
        "Values of type: RDFString",
        "First pass: foo (source=%s)" % self.client_id,
        "Second pass: foo (source=%s)" % self.client_id,
        "Finish: aff4:/foo/bar"
    ])  # pyformat: disable

  def testUsesDefaultClientURNIfGrrMessageHasNoSource(self):
    with self.pool:
      self.collection.Add(
          rdf_flows.GrrMessage(payload=rdfvalue.RDFString("foo"), source=None),
          mutation_pool=self.pool)

    chunks = self.ProcessPlugin(
        source_urn=rdf_client.ClientURN("C.1111222233334444"))

    self.assertListEqual(chunks, [
        "Start: aff4:/foo/bar",
        "Values of type: RDFString",
        "First pass: foo (source=aff4:/C.1111222233334444)",
        "Second pass: foo (source=aff4:/C.1111222233334444)",
        "Finish: aff4:/foo/bar"
    ])  # pyformat: disable

  def testCorrectlyExportsTwoValuesOfTheSameType(self):
    with self.pool:
      self.collection.Add(
          rdf_flows.GrrMessage(
              payload=rdfvalue.RDFString("foo"), source=self.client_id),
          mutation_pool=self.pool)
      self.collection.Add(
          rdf_flows.GrrMessage(
              payload=rdfvalue.RDFString("bar"), source=self.client_id),
          mutation_pool=self.pool)

    chunks = self.ProcessPlugin()

    self.assertListEqual(chunks, [
        "Start: aff4:/foo/bar",
        "Values of type: RDFString",
        "First pass: foo (source=%s)" % self.client_id,
        "First pass: bar (source=%s)" % self.client_id,
        "Second pass: foo (source=%s)" % self.client_id,
        "Second pass: bar (source=%s)" % self.client_id,
        "Finish: aff4:/foo/bar"
    ])  # pyformat: disable

  def testCorrectlyExportsFourValuesOfTwoDifferentTypes(self):
    with self.pool:
      self.collection.Add(
          rdf_flows.GrrMessage(
              payload=rdfvalue.RDFString("foo"), source=self.client_id),
          mutation_pool=self.pool)
      self.collection.Add(
          rdf_flows.GrrMessage(
              payload=rdfvalue.RDFInteger(42), source=self.client_id),
          mutation_pool=self.pool)
      self.collection.Add(
          rdf_flows.GrrMessage(
              payload=rdfvalue.RDFString("bar"), source=self.client_id),
          mutation_pool=self.pool)
      self.collection.Add(
          rdf_flows.GrrMessage(
              payload=rdfvalue.RDFInteger(43), source=self.client_id),
          mutation_pool=self.pool)

    chunks = self.ProcessPlugin()

    self.assertListEqual(chunks, [
        "Start: aff4:/foo/bar",
        "Values of type: RDFInteger",
        "First pass: 42 (source=%s)" % self.client_id,
        "First pass: 43 (source=%s)" % self.client_id,
        "Second pass: 42 (source=%s)" % self.client_id,
        "Second pass: 43 (source=%s)" % self.client_id,
        "Values of type: RDFString",
        "First pass: foo (source=%s)" % self.client_id,
        "First pass: bar (source=%s)" % self.client_id,
        "Second pass: foo (source=%s)" % self.client_id,
        "Second pass: bar (source=%s)" % self.client_id,
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


@db_test_lib.DualDBTest
class InstantOutputPluginWithExportConversionTest(
    test_plugins.InstantOutputPluginTestBase):
  """Tests for InstantOutputPluginWithExportConversion."""

  plugin_cls = test_plugins.TestInstantOutputPluginWithExportConverstion

  def ProcessValuesToLines(self, values_by_cls):
    fd_name = self.ProcessValues(values_by_cls)
    with open(fd_name, "r") as fd:
      return fd.read().split("\n")

  def testWorksCorrectlyWithOneSourceValueAndOneExportedValue(self):
    lines = self.ProcessValuesToLines({DummySrcValue1: [DummySrcValue1("foo")]})
    self.assertListEqual(lines, [
        "Start",
        "Original: DummySrcValue1",
        "Exported value: exp-foo",
        "Finish"
    ])  # pyformat: disable

  def testWorksCorrectlyWithOneSourceValueAndTwoExportedValues(self):
    lines = self.ProcessValuesToLines({DummySrcValue2: [DummySrcValue2("foo")]})
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
        DummySrcValue2: [DummySrcValue2("foo"),
                         DummySrcValue2("bar")]
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
