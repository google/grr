#!/usr/bin/env python
import io
from typing import Iterable, Iterator

from absl import app

from google.protobuf import any_pb2
from google.protobuf import message
from grr_response_core.lib import rdfvalue
from grr_response_proto import export_pb2
from grr_response_proto import flows_pb2
from grr_response_proto import tests_pb2
from grr_response_server import instant_output_plugin
from grr_response_server.export_converters import base
from grr_response_server.output_plugins import test_plugins
from grr.test_lib import export_test_lib
from grr.test_lib import test_lib


class TestConverterProto1(base.ExportConverterProto):
  input_proto_type = tests_pb2.DummySrcValueProto1

  def Convert(
      self,
      metadata: export_pb2.ExportedMetadata,
      value: tests_pb2.DummySrcValueProto1,
  ) -> Iterable[tests_pb2.DummyOutValueProto1]:
    del metadata  # Unused.
    return [tests_pb2.DummyOutValueProto1(value=f"exp-{value.value}")]


class TestConverterProto2(base.ExportConverterProto):
  input_proto_type = tests_pb2.DummySrcValueProto2

  def Convert(
      self,
      metadata: export_pb2.ExportedMetadata,
      value: tests_pb2.DummySrcValueProto2,
  ) -> Iterable[tests_pb2.DummyOutValueProto1 | tests_pb2.DummyOutValueProto2]:
    del metadata  # Unused.
    return [
        tests_pb2.DummyOutValueProto1(value=f"exp1-{value.value}"),
        tests_pb2.DummyOutValueProto2(value=f"exp2-{value.value}"),
    ]


class TestInstantOutputPluginWithExportConversionProto(
    instant_output_plugin.InstantOutputPluginWithExportConversionProto
):
  """Test plugin with export conversion."""

  plugin_name = "test-proto"
  friendly_name = "test plugin proto"
  description = "test plugin description proto"

  def Start(self):
    yield "Start\n".encode("utf-8")

  def ProcessUniqueOriginalExportedTypePair(
      self, original_type_name: str, exported_values: Iterable[message.Message]
  ) -> Iterator[bytes]:
    yield (f"Original: {original_type_name}\n").encode("utf-8")

    for item in exported_values:
      yield (f"Exported value: {item.value}\n").encode("utf-8")

  def Finish(self):
    yield "Finish".encode("utf-8")


class InstantOutputPluginWithExportConversionProtoTest(
    test_plugins.InstantOutputPluginTestBase
):
  """Tests for InstantOutputPluginWithExportConversionProto."""

  plugin_cls = TestInstantOutputPluginWithExportConversionProto

  def ProcessValuesToLines(self, values_by_cls):
    fd_name = self.ProcessValuesProto(values_by_cls)
    with io.open(fd_name, mode="r", encoding="utf-8") as fd:
      return fd.read().split("\n")

  @export_test_lib.WithAllExportConverters
  @export_test_lib.WithExportConverterProto(TestConverterProto1)
  @export_test_lib.WithExportConverterProto(TestConverterProto2)
  def testWorksCorrectlyWithOneSourceValueAndOneExportedValue(self):
    lines = self.ProcessValuesToLines({
        tests_pb2.DummySrcValueProto1: [
            tests_pb2.DummySrcValueProto1(value="foo")
        ]
    })
    self.assertListEqual(
        lines,
        [
            "Start",
            "Original: DummySrcValueProto1",
            "Exported value: exp-foo",
            "Finish",
        ],
    )

  @export_test_lib.WithAllExportConverters
  @export_test_lib.WithExportConverterProto(TestConverterProto1)
  @export_test_lib.WithExportConverterProto(TestConverterProto2)
  def testWorksCorrectlyWithOneSourceValueAndTwoExportedValues(self):
    lines = self.ProcessValuesToLines({
        tests_pb2.DummySrcValueProto2: [
            tests_pb2.DummySrcValueProto2(value="foo")
        ]
    })
    self.assertListEqual(
        lines,
        [
            "Start",
            "Original: DummySrcValueProto2",
            "Exported value: exp1-foo",
            "Original: DummySrcValueProto2",
            "Exported value: exp2-foo",
            "Finish",
        ],
    )

  @export_test_lib.WithAllExportConverters
  @export_test_lib.WithExportConverterProto(TestConverterProto1)
  @export_test_lib.WithExportConverterProto(TestConverterProto2)
  def testWorksCorrectlyWithTwoSourceValueAndTwoExportedValuesEach(self):
    lines = self.ProcessValuesToLines({
        tests_pb2.DummySrcValueProto2: [
            tests_pb2.DummySrcValueProto2(value="foo"),
            tests_pb2.DummySrcValueProto2(value="bar"),
        ]
    })
    self.assertListEqual(
        lines,
        [
            "Start",
            "Original: DummySrcValueProto2",
            "Exported value: exp1-foo",
            "Exported value: exp1-bar",
            "Original: DummySrcValueProto2",
            "Exported value: exp2-foo",
            "Exported value: exp2-bar",
            "Finish",
        ],
    )

  @export_test_lib.WithAllExportConverters
  @export_test_lib.WithExportConverterProto(TestConverterProto1)
  @export_test_lib.WithExportConverterProto(TestConverterProto2)
  def testWorksCorrectlyWithTwoDifferentTypesOfSourceValues(self):
    lines = self.ProcessValuesToLines({
        tests_pb2.DummySrcValueProto1: [
            tests_pb2.DummySrcValueProto1(value="foo")
        ],
        tests_pb2.DummySrcValueProto2: [
            tests_pb2.DummySrcValueProto2(value="bar")
        ],
    })
    self.assertListEqual(
        lines,
        [
            "Start",
            "Original: DummySrcValueProto1",
            "Exported value: exp-foo",
            "Original: DummySrcValueProto2",
            "Exported value: exp1-bar",
            "Original: DummySrcValueProto2",
            "Exported value: exp2-bar",
            "Finish",
        ],
    )


class GetExportedFlowResultsTest(test_lib.GRRBaseTest):

  @export_test_lib.WithAllExportConverters
  @export_test_lib.WithExportConverterProto(TestConverterProto1)
  @export_test_lib.WithExportConverterProto(TestConverterProto2)
  def testGetExportedFlowResults(self):
    hunt_urn = rdfvalue.RDFURN("hunts/H:123456")
    plugin = TestInstantOutputPluginWithExportConversionProto(
        source_urn=hunt_urn
    )

    client_ids = [self.SetupClient(0), self.SetupClient(1), self.SetupClient(2)]

    type_url1 = f"type.googleapis.com/{tests_pb2.DummySrcValueProto1.DESCRIPTOR.full_name}"
    type_url2 = f"type.googleapis.com/{tests_pb2.DummySrcValueProto2.DESCRIPTOR.full_name}"

    def fetch_fn(type_url: str) -> Iterator[flows_pb2.FlowResult]:
      for i, client_id in enumerate(client_ids):
        if type_url == type_url1:
          payload = tests_pb2.DummySrcValueProto1(value=f"foo{i}")
          any_payload = any_pb2.Any()
          any_payload.Pack(payload)
          yield flows_pb2.FlowResult(client_id=client_id, payload=any_payload)
        elif type_url == type_url2:
          payload = tests_pb2.DummySrcValueProto2(value=f"bar{i}")
          any_payload = any_pb2.Any()
          any_payload.Pack(payload)
          yield flows_pb2.FlowResult(client_id=client_id, payload=any_payload)

    chunks = instant_output_plugin.GetExportedFlowResults(
        plugin,
        [type_url1, type_url2],
        fetch_fn,
    )
    output = b"".join(chunks).decode("utf-8").split("\n")
    self.assertListEqual(
        output,
        [
            "Start",
            "Original: DummySrcValueProto1",
            "Exported value: exp-foo0",
            "Exported value: exp-foo1",
            "Exported value: exp-foo2",
            "Original: DummySrcValueProto2",
            "Exported value: exp1-bar0",
            "Exported value: exp1-bar1",
            "Exported value: exp1-bar2",
            "Original: DummySrcValueProto2",
            "Exported value: exp2-bar0",
            "Exported value: exp2-bar1",
            "Exported value: exp2-bar2",
            "Finish",
        ],
    )


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
