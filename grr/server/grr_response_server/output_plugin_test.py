#!/usr/bin/env python
"""Tests for grr.lib.output_plugin."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib import flags
from grr_response_core.lib import registry
from grr_response_core.lib import utils
from grr_response_server import output_plugin
from grr_response_server.flows.general import transfer
from grr_response_server.rdfvalues import flow_runner as rdf_flow_runner
from grr_response_server.rdfvalues import output_plugin as rdf_output_plugin
from grr.test_lib import test_lib


class TestOutputPluginWithArgs(output_plugin.OutputPlugin):

  args_type = rdf_flow_runner.FlowRunnerArgs

  def ProcessResponses(self, state, responses):
    pass


class OutputPluginTest(test_lib.GRRBaseTest):

  def testGetPluginArgsHandlesMissingPluginsCorrectly(self):
    descriptor = rdf_output_plugin.OutputPluginDescriptor(
        plugin_name="TestOutputPluginWithArgs",
        plugin_args=rdf_flow_runner.FlowRunnerArgs(
            flow_name=transfer.GetFile.__name__))
    serialized = descriptor.SerializeToString()

    deserialized = rdf_output_plugin.OutputPluginDescriptor()
    deserialized.ParseFromString(serialized)
    self.assertEqual(deserialized, descriptor)
    self.assertEqual(deserialized.GetPluginClass(), TestOutputPluginWithArgs)

    opr = registry.OutputPluginRegistry
    with utils.Stubber(opr, "PLUGIN_REGISTRY", opr.PLUGIN_REGISTRY.copy()):
      del opr.PLUGIN_REGISTRY["TestOutputPluginWithArgs"]

      deserialized = rdf_output_plugin.OutputPluginDescriptor()
      deserialized.ParseFromString(serialized)

      self.assertTrue(deserialized.GetPluginClass(),
                      output_plugin.UnknownOutputPlugin)
      # UnknownOutputPlugin should just return serialized arguments as bytes.
      self.assertEqual(deserialized.plugin_args,
                       descriptor.plugin_args.SerializeToString())


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
