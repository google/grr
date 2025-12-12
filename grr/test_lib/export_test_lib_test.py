#!/usr/bin/env python
from typing import Any, Callable
from unittest import mock

from absl.testing import absltest

from google.protobuf import wrappers_pb2
from google.protobuf import message
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import export_pb2
from grr_response_server import export_converters_registry
from grr_response_server.export_converters import base
from grr_response_server.export_converters import registry_init
from grr.test_lib import export_test_lib


class FooRDF(rdf_structs.RDFProtoStruct):
  pass


class FooExportConverter(base.ExportConverter):
  input_rdf_type = FooRDF

  def Convert(self, metadata, value):
    raise NotImplementedError()


class FooExportConverter2(base.ExportConverter):
  input_rdf_type = FooRDF

  def Convert(self, metadata, value):
    raise NotImplementedError()


class BarExportConverter(base.ExportConverter):

  def Convert(self, metadata, value):
    raise NotImplementedError()


class BazExportConverter(base.ExportConverter):

  def Convert(self, metadata, value):
    raise NotImplementedError()


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


class WithExportConverterTest(absltest.TestCase):

  def testSingleExportConverter(self):

    @export_test_lib.WithExportConverter(FooExportConverter)
    def AssertFooIsRegistered():
      self.assertSetEqual(export_converters_registry._EXPORT_CONVERTER_REGISTRY,
                          set([FooExportConverter]))

    # By default, nothing should be registered.
    self.assertEmpty(export_converters_registry._EXPORT_CONVERTER_REGISTRY)

    # This function is annotated and should register defined parsers.
    AssertFooIsRegistered()

    # When exiting the context, the ExportConverter should be unregistered.
    self.assertEmpty(export_converters_registry._EXPORT_CONVERTER_REGISTRY)

  def testMultipleExportConverters(self):

    @export_test_lib.WithExportConverter(FooExportConverter)
    @export_test_lib.WithExportConverter(BarExportConverter)
    @export_test_lib.WithExportConverter(BazExportConverter)
    def AssertTestExportConvertersAreRegistered():
      self.assertSetEqual(
          export_converters_registry._EXPORT_CONVERTER_REGISTRY,
          set([FooExportConverter, BarExportConverter, BazExportConverter]))

    # Again, nothing should be registered by default.
    self.assertEmpty(export_converters_registry._EXPORT_CONVERTER_REGISTRY)

    # Every annotation should register corresponding ExportConverter.
    AssertTestExportConvertersAreRegistered()

    # When exiting the context, the ExportConverters should be unregistered,
    # leaving a clean state.
    self.assertEmpty(export_converters_registry._EXPORT_CONVERTER_REGISTRY)


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

  def testWithCustomRegisterMethod_OnlyRDFs(self):

    def Register():
      export_converters_registry.Register(FooExportConverter)
      export_converters_registry.Register(BarExportConverter)
      export_converters_registry.Register(BazExportConverter)

    @export_test_lib.WithAllExportConverters
    def AssertAllTestExportConvertersAreRegistered():
      self.assertSetEqual(
          export_converters_registry._EXPORT_CONVERTER_REGISTRY,
          set([FooExportConverter, BarExportConverter, BazExportConverter]))

    with mock.patch.object(registry_init, "RegisterExportConverters", Register):
      self.assertEmpty(export_converters_registry._EXPORT_CONVERTER_REGISTRY)

      AssertAllTestExportConvertersAreRegistered()

      self.assertEmpty(export_converters_registry._EXPORT_CONVERTER_REGISTRY)

  def testWithCustomMethod_OnlyProtos(self):

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

  def testWithCustomMethod_Mixed(self):

    def Register():
      export_converters_registry.Register(FooExportConverter)
      export_converters_registry.Register(BarExportConverter)
      export_converters_registry.Register(BazExportConverter)
      export_converters_registry.RegisterProto(StringProtoConverterOne)
      export_converters_registry.RegisterProto(StringProtoConverterTwo)
      export_converters_registry.RegisterProto(BytesProtoConverter)

    @export_test_lib.WithAllExportConverters
    def AssertAllTestExportConvertersAreRegistered():
      self.assertSetEqual(
          export_converters_registry._EXPORT_CONVERTER_REGISTRY,
          set([FooExportConverter, BarExportConverter, BazExportConverter]),
      )
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
      self.assertEmpty(export_converters_registry._EXPORT_CONVERTER_REGISTRY)
      AssertEmptySetsForInputProto(self.assertEmpty, wrappers_pb2.StringValue)
      AssertEmptySetsForInputProto(self.assertEmpty, wrappers_pb2.BytesValue)

      AssertAllTestExportConvertersAreRegistered()

      self.assertEmpty(export_converters_registry._EXPORT_CONVERTER_REGISTRY)
      AssertEmptySetsForInputProto(self.assertEmpty, wrappers_pb2.StringValue)
      AssertEmptySetsForInputProto(self.assertEmpty, wrappers_pb2.BytesValue)


class WithAllExportConvertersAndWithExportConverterTest(absltest.TestCase):

  def testAllPlusSome(self):

    def Register():
      export_converters_registry.Register(FooExportConverter)
      export_converters_registry.RegisterProto(StringProtoConverterOne)

    @export_test_lib.WithAllExportConverters
    @export_test_lib.WithExportConverter(BarExportConverter)
    @export_test_lib.WithExportConverter(BazExportConverter)
    @export_test_lib.WithExportConverterProto(StringProtoConverterTwo)
    @export_test_lib.WithExportConverterProto(BytesProtoConverter)
    def AssertAllTestExportConvertersAreRegistered():
      self.assertSetEqual(
          export_converters_registry._EXPORT_CONVERTER_REGISTRY,
          set([FooExportConverter, BarExportConverter, BazExportConverter]))
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
      self.assertEmpty(export_converters_registry._EXPORT_CONVERTER_REGISTRY)
      AssertEmptySetsForInputProto(self.assertEmpty, wrappers_pb2.StringValue)
      AssertEmptySetsForInputProto(self.assertEmpty, wrappers_pb2.BytesValue)

      AssertAllTestExportConvertersAreRegistered()

      self.assertEmpty(export_converters_registry._EXPORT_CONVERTER_REGISTRY)
      AssertEmptySetsForInputProto(self.assertEmpty, wrappers_pb2.StringValue)
      AssertEmptySetsForInputProto(self.assertEmpty, wrappers_pb2.BytesValue)


if __name__ == "__main__":
  absltest.main()
