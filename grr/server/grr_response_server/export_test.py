#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""Tests for export converters."""

from absl import app

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import cloud as rdf_cloud
from grr_response_server import data_store
from grr_response_server import export
from grr_response_server.export_converters import base
from grr.test_lib import export_test_lib
from grr.test_lib import fixture_test_lib
from grr.test_lib import test_lib


class DummyRDFValue(rdfvalue.RDFString):
  pass


class DummyRDFValue2(rdfvalue.RDFString):
  pass


class DummyRDFValue3(rdfvalue.RDFString):
  pass


class DummyRDFValue4(rdfvalue.RDFString):
  pass


class DummyRDFValueConverter(base.ExportConverter):
  input_rdf_type = DummyRDFValue

  def Convert(self, metadata, value):
    _ = metadata
    return [rdfvalue.RDFString(str(value))]


class DummyRDFValue3ConverterA(base.ExportConverter):
  input_rdf_type = DummyRDFValue3

  def Convert(self, metadata, value):
    _ = metadata
    return [DummyRDFValue(str(value) + "A")]


class DummyRDFValue3ConverterB(base.ExportConverter):
  input_rdf_type = DummyRDFValue3

  def Convert(self, metadata, value):
    _ = metadata
    if not isinstance(value, DummyRDFValue3):
      raise ValueError("Called with the wrong type")
    return [DummyRDFValue2(str(value) + "B")]


class DummyRDFValue4ToMetadataConverter(base.ExportConverter):
  input_rdf_type = DummyRDFValue4

  def Convert(self, metadata, value):
    _ = value
    return [metadata]


class ConvertValuesTest(export_test_lib.ExportTestBase):
  """Tests the ConvertValues function."""

  @export_test_lib.WithExportConverter(DummyRDFValueConverter)
  def testConverterIsCorrectlyFound(self):
    dummy_value = DummyRDFValue("result")
    result = list(export.ConvertValues(self.metadata, [dummy_value]))
    self.assertLen(result, 1)
    self.assertIsInstance(result[0], rdfvalue.RDFString)
    self.assertEqual(result[0], "result")

  def testDoesNotRaiseWhenNoSpecificConverterIsDefined(self):
    dummy_value = DummyRDFValue2("some")
    export.ConvertValues(self.metadata, [dummy_value])

  def testDataAgnosticConverterIsUsedWhenNoSpecificConverterIsDefined(self):
    original_value = export_test_lib.DataAgnosticConverterTestValue()

    # There's no converter defined for
    # export_test_lib.DataAgnosticConverterTestValue,
    # so we expect DataAgnosticExportConverter to be used.
    converted_values = list(
        export.ConvertValues(self.metadata, [original_value]))
    self.assertLen(converted_values, 1)
    converted_value = converted_values[0]

    self.assertEqual(converted_value.__class__.__name__,
                     "AutoExportedDataAgnosticConverterTestValue")

  @export_test_lib.WithExportConverter(DummyRDFValue3ConverterA)
  @export_test_lib.WithExportConverter(DummyRDFValue3ConverterB)
  def testConvertsSingleValueWithMultipleAssociatedConverters(self):
    dummy_value = DummyRDFValue3("some")
    result = list(export.ConvertValues(self.metadata, [dummy_value]))
    self.assertLen(result, 2)
    self.assertTrue((isinstance(result[0], DummyRDFValue) and
                     isinstance(result[1], DummyRDFValue2)) or
                    (isinstance(result[0], DummyRDFValue2) and
                     isinstance(result[1], DummyRDFValue)))
    self.assertTrue((result[0] == DummyRDFValue("someA") and
                     result[1] == DummyRDFValue2("someB")) or
                    (result[0] == DummyRDFValue2("someB") and
                     result[1] == DummyRDFValue("someA")))


class GetMetadataTest(test_lib.GRRBaseTest):

  def setUp(self):
    super().setUp()
    self.client_id = "C.4815162342108107"

  def testGetMetadataWithSingleUserLabel(self):
    fixture_test_lib.ClientFixture(self.client_id)
    self.AddClientLabel(self.client_id, self.test_username, "client-label-24")

    metadata = export.GetMetadata(
        self.client_id, data_store.REL_DB.ReadClientFullInfo(self.client_id))
    self.assertEqual(metadata.os, "Windows")
    self.assertEqual(metadata.labels, "client-label-24")
    self.assertEqual(metadata.user_labels, "client-label-24")
    self.assertEqual(metadata.system_labels, "")
    self.assertEqual(metadata.hardware_info.bios_version, "Version 1.23v")

  def testGetMetadataWithTwoUserLabels(self):
    fixture_test_lib.ClientFixture(self.client_id)
    self.AddClientLabel(self.client_id, self.test_username, "a")
    self.AddClientLabel(self.client_id, self.test_username, "b")

    metadata = export.GetMetadata(
        self.client_id, data_store.REL_DB.ReadClientFullInfo(self.client_id))
    self.assertEqual(metadata.os, "Windows")
    self.assertEqual(metadata.labels, "a,b")
    self.assertEqual(metadata.user_labels, "a,b")
    self.assertEqual(metadata.system_labels, "")

  def testGetMetadataWithSystemLabels(self):
    fixture_test_lib.ClientFixture(self.client_id)
    self.AddClientLabel(self.client_id, self.test_username, "a")
    self.AddClientLabel(self.client_id, self.test_username, "b")
    self.AddClientLabel(self.client_id, "GRR", "c")

    metadata = export.GetMetadata(
        self.client_id, data_store.REL_DB.ReadClientFullInfo(self.client_id))
    self.assertEqual(metadata.labels, "a,b,c")
    self.assertEqual(metadata.user_labels, "a,b")
    self.assertEqual(metadata.system_labels, "c")

  def testGetMetadataMissingKB(self):
    # We do not want to use `self.client_id` in this test because we need an
    # uninitialized client.
    client_id = "C.4815162342108108"
    data_store.REL_DB.WriteClientMetadata(
        client_id, first_seen=rdfvalue.RDFDatetime(42))

    # Expect empty usernames field due to no knowledge base.
    metadata = export.GetMetadata(
        client_id, data_store.REL_DB.ReadClientFullInfo(client_id))
    self.assertFalse(metadata.usernames)

  def testGetMetadataWithoutCloudInstanceSet(self):
    fixture_test_lib.ClientFixture(self.client_id)

    metadata = export.GetMetadata(
        self.client_id, data_store.REL_DB.ReadClientFullInfo(self.client_id))
    self.assertFalse(metadata.HasField("cloud_instance_type"))
    self.assertFalse(metadata.HasField("cloud_instance_id"))

  def testGetMetadataWithGoogleCloudInstanceID(self):
    fixture_test_lib.ClientFixture(self.client_id)
    snapshot = data_store.REL_DB.ReadClientSnapshot(self.client_id)
    snapshot.cloud_instance = rdf_cloud.CloudInstance(
        cloud_type=rdf_cloud.CloudInstance.InstanceType.GOOGLE,
        google=rdf_cloud.GoogleCloudInstance(unique_id="foo/bar"))
    data_store.REL_DB.WriteClientSnapshot(snapshot)

    metadata = export.GetMetadata(
        self.client_id, data_store.REL_DB.ReadClientFullInfo(self.client_id))
    self.assertEqual(metadata.cloud_instance_type,
                     metadata.CloudInstanceType.GOOGLE)
    self.assertEqual(metadata.cloud_instance_id, "foo/bar")

  def testGetMetadataWithAmazonCloudInstanceID(self):
    fixture_test_lib.ClientFixture(self.client_id)
    snapshot = data_store.REL_DB.ReadClientSnapshot(self.client_id)
    snapshot.cloud_instance = rdf_cloud.CloudInstance(
        cloud_type=rdf_cloud.CloudInstance.InstanceType.AMAZON,
        amazon=rdf_cloud.AmazonCloudInstance(instance_id="foo/bar"))
    data_store.REL_DB.WriteClientSnapshot(snapshot)

    metadata = export.GetMetadata(
        self.client_id, data_store.REL_DB.ReadClientFullInfo(self.client_id))
    self.assertEqual(metadata.cloud_instance_type,
                     metadata.CloudInstanceType.AMAZON)
    self.assertEqual(metadata.cloud_instance_id, "foo/bar")


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
