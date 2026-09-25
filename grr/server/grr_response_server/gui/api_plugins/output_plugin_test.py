#!/usr/bin/env python
"""This module contains tests for output plugin API handlers."""

from absl import app

from google.protobuf import any_pb2
from grr_response_proto import jobs_pb2
from grr_response_proto.api import reflection_pb2
from grr_response_server import output_plugin
from grr_response_server.gui import api_test_lib
from grr_response_server.gui.api_plugins import output_plugin as output_plugin_plugin
from grr_response_server.output_plugins import test_plugins
from grr.test_lib import test_lib


class DummyOutputPluginProto(
    output_plugin.OutputPluginProto[jobs_pb2.LogMessage]
):
  name = "proto"
  friendly_name = "friendly"
  description = "desc"
  args_type = jobs_pb2.LogMessage


class ApiListOutputPluginDescriptorsHandlerTest(
    api_test_lib.ApiCallHandlerTest
):
  """Test for ApiListOutputPluginDescriptorsHandler."""

  def setUp(self):
    super().setUp()
    self.handler = output_plugin_plugin.ApiListOutputPluginDescriptorsHandler()

  @test_plugins.WithOutputPluginProto(DummyOutputPluginProto)
  def testRendersOutputPlugins(self):
    result = self.handler.Handle(None, context=self.context)
    self.assertLen(result.items, 1)

    proto_item = result.items[0]
    self.assertEqual(proto_item.name, DummyOutputPluginProto.__name__)
    self.assertEqual(proto_item.description, DummyOutputPluginProto.description)
    self.assertEqual(
        proto_item.friendly_name, DummyOutputPluginProto.friendly_name
    )
    packed_log_message = any_pb2.Any()
    packed_log_message.Pack(jobs_pb2.LogMessage())
    self.assertEqual(proto_item.args_type, packed_log_message.type_url)
    self.assertEqual(
        proto_item.plugin_type,
        reflection_pb2.ApiOutputPluginDescriptor.PluginType.LEGACY,
    )


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
