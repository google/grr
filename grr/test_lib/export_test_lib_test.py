#!/usr/bin/env python
from typing import Any, Callable
from unittest import mock

from absl.testing import absltest

from google.protobuf import wrappers_pb2
from google.protobuf import message
from grr_response_proto import export_pb2
from grr_response_server import export_converters_registry
from grr_response_server.export_converters import base
from grr_response_server.export_converters import registry_init
from grr.test_lib import export_test_lib


class StringProtoConverterOne(
    base.ExportConverterProto[wrappers_pb2.StringValue]
):
  input_proto_type = wrappers_pb2.StringValue
  output_proto_types = (export_pb2.ExportedString,)

  def Convert(
      self,
      metadata: export_pb2.ExportedMetadata,
      value: wrappers_pb2.StringValue,
  ):
    raise NotImplementedError()


class StringProtoConverterTwo(
    base.ExportConverterProto[wrappers_pb2.StringValue]
):
  input_proto_type = wrappers_pb2.StringValue
  output_proto_types = (export_pb2.ExportedString,)

  def Convert(
      self,
      metadata: export_pb2.ExportedMetadata,
      value: wrappers_pb2.StringValue,
  ):
    raise NotImplementedError()


class BytesProtoConverter(base.ExportConverterProto[wrappers_pb2.BytesValue]):
  input_proto_type = wrappers_pb2.BytesValue
  output_proto_types = (export_pb2.ExportedBytes,)

  def Convert(
      self,
      metadata: export_pb2.ExportedMetadata,
      value: wrappers_pb2.BytesValue,
  ):
    raise NotImplementedError()


def AssertEmptySetsForInputProto(
    assert_fn: Callable[[Any], None], proto_cls: type[message.Message]
):
  assert_fn(
      export_converters_registry._EXPORT_CONVERTER_REGISTRY_BY_PROTO_CLS[
          proto_cls
      ]
  )
  assert_fn(
      export_converters_registry._EXPORT_CONVERTER_BY_TYPE_URL[
          f"type.googleapis.com/{proto_cls.DESCRIPTOR.full_name}"
      ]
  )


def GetSetsForProto(
    proto_cls: type[message.Message],
) -> tuple[set[base.ExportConverterProto], set[base.ExportConverterProto]]:
  return (
      export_converters_registry._EXPORT_CONVERTER_REGISTRY_BY_PROTO_CLS[
          proto_cls
      ],
      export_converters_registry._EXPORT_CONVERTER_BY_TYPE_URL[
          f"type.googleapis.com/{proto_cls.DESCRIPTOR.full_name}"
      ],
  )


class WithExportConverterProtoTest(absltest.TestCase):

  def testSingleExportConverter(self):

    @export_test_lib.WithExportConverterProto(StringProtoConverterOne)
    def AssertFooIsRegistered():
      set_by_cls, set_by_type_url = GetSetsForProto(wrappers_pb2.StringValue)
      self.assertSetEqual(set_by_cls, set([StringProtoConverterOne]))
      self.assertSetEqual(set_by_type_url, set([StringProtoConverterOne]))

    # By default, we should get empty sets for the registries.
    AssertEmptySetsForInputProto(self.assertEmpty, wrappers_pb2.StringValue)
    AssertEmptySetsForInputProto(self.assertEmpty, wrappers_pb2.BytesValue)

    # In the context, the ExportConverter should be registered. We assert it
    # inside the function to make sure.
    AssertFooIsRegistered()

    # When exiting the context, the sets should be empty again.
    AssertEmptySetsForInputProto(self.assertEmpty, wrappers_pb2.StringValue)
    AssertEmptySetsForInputProto(self.assertEmpty, wrappers_pb2.BytesValue)

  def testMultipleExportConverters(self):

    @export_test_lib.WithExportConverterProto(StringProtoConverterOne)
    @export_test_lib.WithExportConverterProto(StringProtoConverterTwo)
    @export_test_lib.WithExportConverterProto(BytesProtoConverter)
    def AssertTestExportConvertersAreRegistered():
      set_by_cls, set_by_type_url = GetSetsForProto(wrappers_pb2.StringValue)
      self.assertSetEqual(
          set_by_cls, set([StringProtoConverterOne, StringProtoConverterTwo])
      )
      self.assertSetEqual(
          set_by_type_url,
          set([StringProtoConverterOne, StringProtoConverterTwo]),
      )
      set_by_cls, set_by_type_url = GetSetsForProto(wrappers_pb2.BytesValue)
      self.assertSetEqual(set_by_cls, set([BytesProtoConverter]))
      self.assertSetEqual(set_by_type_url, set([BytesProtoConverter]))

    AssertEmptySetsForInputProto(self.assertEmpty, wrappers_pb2.StringValue)
    AssertEmptySetsForInputProto(self.assertEmpty, wrappers_pb2.BytesValue)

    AssertTestExportConvertersAreRegistered()

    AssertEmptySetsForInputProto(self.assertEmpty, wrappers_pb2.StringValue)
    AssertEmptySetsForInputProto(self.assertEmpty, wrappers_pb2.BytesValue)


class WithAllExportConvertersTest(absltest.TestCase):

  def testWithCustomMethod(self):

    def Register():
      export_converters_registry.RegisterProto(StringProtoConverterOne)
      export_converters_registry.RegisterProto(StringProtoConverterTwo)
      export_converters_registry.RegisterProto(BytesProtoConverter)

    @export_test_lib.WithAllExportConverters
    def AssertAllTestExportConvertersAreRegistered():
      set_by_cls, set_by_type_url = GetSetsForProto(wrappers_pb2.StringValue)
      self.assertSetEqual(
          set_by_cls, set([StringProtoConverterOne, StringProtoConverterTwo])
      )
      self.assertSetEqual(
          set_by_type_url,
          set([StringProtoConverterOne, StringProtoConverterTwo]),
      )
      set_by_cls, set_by_type_url = GetSetsForProto(wrappers_pb2.BytesValue)
      self.assertSetEqual(set_by_cls, set([BytesProtoConverter]))
      self.assertSetEqual(set_by_type_url, set([BytesProtoConverter]))

    with mock.patch.object(registry_init, "RegisterExportConverters", Register):
      AssertEmptySetsForInputProto(self.assertEmpty, wrappers_pb2.StringValue)
      AssertEmptySetsForInputProto(self.assertEmpty, wrappers_pb2.BytesValue)

      AssertAllTestExportConvertersAreRegistered()

      AssertEmptySetsForInputProto(self.assertEmpty, wrappers_pb2.StringValue)
      AssertEmptySetsForInputProto(self.assertEmpty, wrappers_pb2.BytesValue)


class WithAllExportConvertersAndWithExportConverterTest(absltest.TestCase):

  def testAllPlusSome(self):

    def Register():
      export_converters_registry.RegisterProto(StringProtoConverterOne)

    @export_test_lib.WithAllExportConverters
    @export_test_lib.WithExportConverterProto(StringProtoConverterTwo)
    @export_test_lib.WithExportConverterProto(BytesProtoConverter)
    def AssertAllTestExportConvertersAreRegistered():
      set_by_cls, set_by_type_url = GetSetsForProto(wrappers_pb2.StringValue)
      self.assertSetEqual(
          set_by_cls, set([StringProtoConverterOne, StringProtoConverterTwo])
      )
      self.assertSetEqual(
          set_by_type_url,
          set([StringProtoConverterOne, StringProtoConverterTwo]),
      )
      set_by_cls, set_by_type_url = GetSetsForProto(wrappers_pb2.BytesValue)
      self.assertSetEqual(set_by_cls, set([BytesProtoConverter]))
      self.assertSetEqual(set_by_type_url, set([BytesProtoConverter]))

    with mock.patch.object(registry_init, "RegisterExportConverters", Register):
      AssertEmptySetsForInputProto(self.assertEmpty, wrappers_pb2.StringValue)
      AssertEmptySetsForInputProto(self.assertEmpty, wrappers_pb2.BytesValue)

      AssertAllTestExportConvertersAreRegistered()

      AssertEmptySetsForInputProto(self.assertEmpty, wrappers_pb2.StringValue)
      AssertEmptySetsForInputProto(self.assertEmpty, wrappers_pb2.BytesValue)


if __name__ == "__main__":
  absltest.main()
