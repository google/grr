#!/usr/bin/env python
from unittest import mock

from absl.testing import absltest

from grr_response_core.lib.rdfvalues import structs as rdf_structs
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


class WithAllExportConvertersTest(absltest.TestCase):

  def testWithCustomRegisterMethod(self):

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


class WithAllExportConvertersAndWithExportConverterTest(absltest.TestCase):

  def testAllPlusSome(self):

    def Register():
      export_converters_registry.Register(FooExportConverter)

    @export_test_lib.WithAllExportConverters
    @export_test_lib.WithExportConverter(BarExportConverter)
    @export_test_lib.WithExportConverter(BazExportConverter)
    def AssertAllTestExportConvertersAreRegistered():
      self.assertSetEqual(
          export_converters_registry._EXPORT_CONVERTER_REGISTRY,
          set([FooExportConverter, BarExportConverter, BazExportConverter]))

    with mock.patch.object(registry_init, "RegisterExportConverters", Register):
      self.assertEmpty(export_converters_registry._EXPORT_CONVERTER_REGISTRY)

      AssertAllTestExportConvertersAreRegistered()

      self.assertEmpty(export_converters_registry._EXPORT_CONVERTER_REGISTRY)


if __name__ == "__main__":
  absltest.main()
