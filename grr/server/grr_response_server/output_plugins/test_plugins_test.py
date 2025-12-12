#!/usr/bin/env python
from absl import app
from absl.testing import absltest

from grr_response_server import instant_output_plugin
from grr_response_server import instant_output_plugin_registry
from grr_response_server import output_plugin
from grr_response_server import output_plugin_registry
from grr_response_server.output_plugins import test_plugins
from grr.test_lib import test_lib


class FooPlugin(instant_output_plugin.InstantOutputPluginProto):
  plugin_name = "foo"
  friendly_name = "Foo"
  description = "Foo plugin"
  output_proto_types = ["google.protobuf.StringValue"]

  def Start(self):
    raise NotImplementedError()

  def ProcessValuesOfType(self, metadata, response):
    raise NotImplementedError()

  def Finish(self):
    raise NotImplementedError()


class BarPlugin(instant_output_plugin.InstantOutputPluginProto):
  plugin_name = "bar"
  friendly_name = "Bar"
  description = "Bar plugin"
  output_proto_types = ["google.protobuf.StringValue"]

  def Start(self):
    raise NotImplementedError()

  def ProcessValuesOfType(self, metadata, response):
    raise NotImplementedError()

  def Finish(self):
    raise NotImplementedError()


class WithInstantOutputPluginProtoTest(absltest.TestCase):

  def testSinglePlugin(self):

    @test_plugins.WithInstantOutputPluginProto(FooPlugin)
    def AssertFooIsRegistered():
      self.assertEqual(
          instant_output_plugin_registry.GetPluginClassByNameProto("foo"),
          FooPlugin,
      )

    with self.assertRaises(KeyError):
      instant_output_plugin_registry.GetPluginClassByNameProto("foo")

    AssertFooIsRegistered()

    with self.assertRaises(KeyError):
      instant_output_plugin_registry.GetPluginClassByNameProto("foo")

  def testMultiplePlugins(self):

    @test_plugins.WithInstantOutputPluginProto(FooPlugin)
    @test_plugins.WithInstantOutputPluginProto(BarPlugin)
    def AssertPluginsAreRegistered():
      self.assertEqual(
          instant_output_plugin_registry.GetPluginClassByNameProto("foo"),
          FooPlugin,
      )
      self.assertEqual(
          instant_output_plugin_registry.GetPluginClassByNameProto("bar"),
          BarPlugin,
      )

    with self.assertRaises(KeyError):
      instant_output_plugin_registry.GetPluginClassByNameProto("foo")


class BazPlugin(output_plugin.OutputPluginProto):
  friendly_name = "baz"
  description = "Baz plugin"

  def ProcessResults(self, responses):
    pass


class QuxPlugin(output_plugin.OutputPluginProto):
  friendly_name = "qux"
  description = "Qux plugin"

  def ProcessResults(self, responses):
    pass


class WithOutputPluginProtoTest(absltest.TestCase):

  def testSinglePlugin(self):

    @test_plugins.WithOutputPluginProto(BazPlugin)
    def AssertBazIsRegistered():
      self.assertEqual(
          output_plugin_registry.GetPluginClassByName("BazPlugin"),
          BazPlugin,
      )

    with self.assertRaises(KeyError):
      output_plugin_registry.GetPluginClassByName("BazPlugin")

    AssertBazIsRegistered()

    with self.assertRaises(KeyError):
      output_plugin_registry.GetPluginClassByName("BazPlugin")

  def testMultiplePlugins(self):

    @test_plugins.WithOutputPluginProto(BazPlugin)
    @test_plugins.WithOutputPluginProto(QuxPlugin)
    def AssertPluginsAreRegistered():
      self.assertEqual(
          output_plugin_registry.GetPluginClassByName("BazPlugin"),
          BazPlugin,
      )
      self.assertEqual(
          output_plugin_registry.GetPluginClassByName("QuxPlugin"),
          QuxPlugin,
      )

    with self.assertRaises(KeyError):
      output_plugin_registry.GetPluginClassByName("BazPlugin")
    with self.assertRaises(KeyError):
      output_plugin_registry.GetPluginClassByName("QuxPlugin")

    AssertPluginsAreRegistered()

    with self.assertRaises(KeyError):
      output_plugin_registry.GetPluginClassByName("BazPlugin")
    with self.assertRaises(KeyError):
      output_plugin_registry.GetPluginClassByName("QuxPlugin")


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
