#!/usr/bin/env python
from absl import app

from grr_response_core.lib import queues
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_server.export_converters import base
from grr_response_server.export_converters import grr_message
from grr.test_lib import export_test_lib
from grr.test_lib import fixture_test_lib
from grr.test_lib import test_lib


class DummyTestRDFValue1(rdfvalue.RDFString):
  pass


class DummyTestRDFValue2(rdfvalue.RDFString):
  pass


class DummyTestRDFValue3(rdfvalue.RDFString):
  pass


class DummyTestRDFValue4(rdfvalue.RDFString):
  pass


class DummyTestRDFValue5(rdfvalue.RDFString):
  pass


class DummyTestRDFValue1Converter(base.ExportConverter):
  input_rdf_type = DummyTestRDFValue1

  def Convert(self, metadata, value):
    _ = metadata
    return [rdfvalue.RDFString(str(value))]


class DummyTestRDFValue3ConverterA(base.ExportConverter):
  input_rdf_type = DummyTestRDFValue3

  def Convert(self, metadata, value):
    _ = metadata
    return [DummyTestRDFValue1(str(value) + "A")]


class DummyTestRDFValue3ConverterB(base.ExportConverter):
  input_rdf_type = DummyTestRDFValue3

  def Convert(self, metadata, value):
    _ = metadata
    if not isinstance(value, DummyTestRDFValue3):
      raise ValueError("Called with the wrong type")
    return [DummyTestRDFValue2(str(value) + "B")]


class DummyTestRDFValue4ToMetadataConverter(base.ExportConverter):
  input_rdf_type = DummyTestRDFValue4

  def Convert(self, metadata, value):
    _ = value
    return [metadata]


class DummyTestRDFValue5Converter(base.ExportConverter):
  input_rdf_type = DummyTestRDFValue5

  def Convert(self, metadata, value):
    _ = metadata
    if not isinstance(value, DummyTestRDFValue5):
      raise ValueError("Called with the wrong type")
    return [DummyTestRDFValue5(str(value) + "C")]


class GrrMessageConverterTest(export_test_lib.ExportTestBase):

  @export_test_lib.WithExportConverter(DummyTestRDFValue4ToMetadataConverter)
  def testGrrMessageConverter(self):
    payload = DummyTestRDFValue4("some")
    msg = rdf_flows.GrrMessage(payload=payload)
    msg.source = self.client_id
    fixture_test_lib.ClientFixture(self.client_id)

    metadata = base.ExportedMetadata(
        source_urn=rdfvalue.RDFURN("aff4:/hunts/" + str(queues.HUNTS) +
                                   ":000000/Results"))

    converter = grr_message.GrrMessageConverter()
    with test_lib.FakeTime(2):
      results = list(converter.Convert(metadata, msg))

    self.assertLen(results, 1)
    self.assertEqual(results[0].timestamp,
                     rdfvalue.RDFDatetime.FromSecondsSinceEpoch(2))
    self.assertEqual(results[0].source_urn,
                     "aff4:/hunts/" + str(queues.HUNTS) + ":000000/Results")

  @export_test_lib.WithExportConverter(DummyTestRDFValue4ToMetadataConverter)
  def testGrrMessageConverterWithOneMissingClient(self):
    client_id_1 = "C.0000000000000000"
    client_id_2 = "C.0000000000000001"

    payload1 = DummyTestRDFValue4("some")
    msg1 = rdf_flows.GrrMessage(payload=payload1)
    msg1.source = client_id_1
    fixture_test_lib.ClientFixture(client_id_1)

    payload2 = DummyTestRDFValue4("some2")
    msg2 = rdf_flows.GrrMessage(payload=payload2)
    msg2.source = client_id_2

    metadata1 = base.ExportedMetadata(
        source_urn=rdfvalue.RDFURN("aff4:/hunts/" + str(queues.HUNTS) +
                                   ":000000/Results"))
    metadata2 = base.ExportedMetadata(
        source_urn=rdfvalue.RDFURN("aff4:/hunts/" + str(queues.HUNTS) +
                                   ":000001/Results"))

    converter = grr_message.GrrMessageConverter()
    with test_lib.FakeTime(3):
      results = list(
          converter.BatchConvert([(metadata1, msg1), (metadata2, msg2)]))

    self.assertLen(results, 1)
    self.assertEqual(results[0].timestamp,
                     rdfvalue.RDFDatetime.FromSecondsSinceEpoch(3))
    self.assertEqual(results[0].source_urn,
                     "aff4:/hunts/" + str(queues.HUNTS) + ":000000/Results")

  @export_test_lib.WithExportConverter(DummyTestRDFValue3ConverterA)
  @export_test_lib.WithExportConverter(DummyTestRDFValue3ConverterB)
  @export_test_lib.WithExportConverter(DummyTestRDFValue5Converter)
  def testGrrMessageConverterMultipleTypes(self):
    payload1 = DummyTestRDFValue3("some")
    client_id = "C.0000000000000000"
    msg1 = rdf_flows.GrrMessage(payload=payload1)
    msg1.source = client_id
    fixture_test_lib.ClientFixture(client_id)

    payload2 = DummyTestRDFValue5("some2")
    msg2 = rdf_flows.GrrMessage(payload=payload2)
    msg2.source = client_id

    metadata1 = base.ExportedMetadata(
        source_urn=rdfvalue.RDFURN("aff4:/hunts/" + str(queues.HUNTS) +
                                   ":000000/Results"))
    metadata2 = base.ExportedMetadata(
        source_urn=rdfvalue.RDFURN("aff4:/hunts/" + str(queues.HUNTS) +
                                   ":000001/Results"))

    converter = grr_message.GrrMessageConverter()
    with test_lib.FakeTime(3):
      results = list(
          converter.BatchConvert([(metadata1, msg1), (metadata2, msg2)]))

    self.assertLen(results, 3)
    # RDFValue3 gets converted to RDFValue2 and RDFValue, RDFValue5 stays at 5.
    self.assertCountEqual(
        ["DummyTestRDFValue2", "DummyTestRDFValue1", "DummyTestRDFValue5"],
        [x.__class__.__name__ for x in results])


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
