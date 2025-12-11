#!/usr/bin/env python
from unittest import mock

from absl import app

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import registry
from grr_response_server import output_plugin
from grr_response_server.flows.general import file_finder
from grr_response_server.rdfvalues import flow_runner as rdf_flow_runner
from grr_response_server.rdfvalues import output_plugin as rdf_output_plugin
from grr.test_lib import test_lib


class TestOutputPluginWithArgs(output_plugin.OutputPlugin):

  args_type = rdf_flow_runner.FlowRunnerArgs

  def ProcessResponses(self, state, responses):
    pass


class OutputPluginTest(test_lib.GRRBaseTest):

  def testGetArgsHandlesMissingPluginsCorrectly(self):
    plugin_args = rdf_flow_runner.FlowRunnerArgs(
        flow_name=file_finder.ClientFileFinder.__name__,
    )
    descriptor = rdf_output_plugin.OutputPluginDescriptor(
        plugin_name="TestOutputPluginWithArgs", args=plugin_args
    )
    serialized = descriptor.SerializeToBytes()

    deserialized = rdf_output_plugin.OutputPluginDescriptor.FromSerializedBytes(
        serialized
    )
    self.assertEqual(deserialized, descriptor)
    self.assertEqual(deserialized.GetPluginClass(), TestOutputPluginWithArgs)

    opr = registry.OutputPluginRegistry
    with mock.patch.object(opr, "PLUGIN_REGISTRY", opr.PLUGIN_REGISTRY.copy()):
      del opr.PLUGIN_REGISTRY["TestOutputPluginWithArgs"]

      deserialized = (
          rdf_output_plugin.OutputPluginDescriptor.FromSerializedBytes(
              serialized
          )
      )

      self.assertEqual(
          deserialized.GetPluginClass(), output_plugin.UnknownOutputPlugin
      )
      # UnknownOutputPlugin should just return serialized arguments as bytes.
      self.assertEqual(deserialized.GetPluginArgsClass(), rdfvalue.RDFBytes)

      self.assertEqual(deserialized.args, descriptor.args.SerializeToBytes())


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
