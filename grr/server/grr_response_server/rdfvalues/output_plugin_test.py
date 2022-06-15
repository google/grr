#!/usr/bin/env python
from absl.testing import absltest

from grr_response_core.lib import registry
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import tests_pb2
from grr_response_server import output_plugin
from grr_response_server.rdfvalues import output_plugin as rdf_output_plugin


class TestOutputPluginArgs(rdf_structs.RDFProtoStruct):
  protobuf = tests_pb2.TestOutputPluginArgs


class TestOutputPlugin(output_plugin.OutputPlugin):
  """A dummy output plugin."""

  name = "test"
  description = "Dummy do do."
  args_type = TestOutputPluginArgs


class OutputPluginTest(absltest.TestCase):

  def setUp(self):
    super().setUp()
    registry.OutputPluginRegistry.PLUGIN_REGISTRY[
        TestOutputPlugin.__name__] = TestOutputPlugin

  def tearDown(self):
    super().tearDown()
    del registry.OutputPluginRegistry.PLUGIN_REGISTRY[TestOutputPlugin.__name__]

  def testGetArgsField(self):
    new_args = rdf_structs.AnyValue.Pack(
        TestOutputPluginArgs(test_message="new"))
    desc = rdf_output_plugin.OutputPluginDescriptor(
        plugin_name=TestOutputPlugin.__name__, args=new_args)
    self.assertEqual(
        desc.args.Unpack(desc.GetPluginArgsClass()),
        TestOutputPluginArgs(test_message="new"))

  def testFallback_BothFields(self):
    new_args = rdf_structs.AnyValue.Pack(
        TestOutputPluginArgs(test_message="new"))
    desc = rdf_output_plugin.OutputPluginDescriptor(
        plugin_name=TestOutputPlugin.__name__,
        plugin_args=TestOutputPluginArgs(test_message="old"),
        args=new_args)
    self.assertEqual(desc.plugin_args, TestOutputPluginArgs(test_message="new"))

  def testFallback_NewOnly(self):
    new_args = rdf_structs.AnyValue.Pack(
        TestOutputPluginArgs(test_message="new"))
    desc = rdf_output_plugin.OutputPluginDescriptor(
        plugin_name=TestOutputPlugin.__name__, args=new_args)

    self.assertEqual(desc.plugin_args, TestOutputPluginArgs(test_message="new"))

  def testFallback_OldOnly(self):
    desc = rdf_output_plugin.OutputPluginDescriptor(
        plugin_name=TestOutputPlugin.__name__,
        plugin_args=TestOutputPluginArgs(test_message="old"))
    self.assertEqual(desc.plugin_args, TestOutputPluginArgs(test_message="old"))


if __name__ == "__main__":
  absltest.main()
