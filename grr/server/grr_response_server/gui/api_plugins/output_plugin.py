#!/usr/bin/env python
"""API handlers for dealing with output_plugins."""

from typing import Optional

from grr_response_proto.api import reflection_pb2
from grr_response_server import output_plugin
from grr_response_server import output_plugin_registry
from grr_response_server.gui import api_call_context
from grr_response_server.gui import api_call_handler_base


def ApiOutputPluginDescriptorFromProtoClass(
    plugin_class: type[output_plugin.OutputPluginProto],
) -> reflection_pb2.ApiOutputPluginDescriptor:
  """Builds an ApiOutputPluginDescriptor proto from an output plugin class.

  Args:
    plugin_class: Python class of the output plugin.

  Returns:
    ApiOutputPluginDescriptor proto based on the given plugin class.

  Raises:
    ValueError: When the plugin class is not known.
  """
  res = reflection_pb2.ApiOutputPluginDescriptor()
  res.name = plugin_class.__name__
  res.friendly_name = plugin_class.friendly_name
  res.description = plugin_class.description
  res.plugin_type = reflection_pb2.ApiOutputPluginDescriptor.PluginType.LEGACY
  if plugin_class.args_type:  # pytype: disable=unbound-type-param
    res.args_type = (
        f"type.googleapis.com/{plugin_class.args_type.DESCRIPTOR.full_name}"
    )

  return res


class ApiListOutputPluginDescriptorsHandler(
    api_call_handler_base.ApiCallHandler
):
  """Renders all available output plugins definitions."""

  proto_result_type = reflection_pb2.ApiListOutputPluginDescriptorsResult

  def Handle(
      self,
      unused_args: None,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> reflection_pb2.ApiListOutputPluginDescriptorsResult:
    items: list[reflection_pb2.ApiOutputPluginDescriptor] = []

    # Handle OutputPluginProto (proto-based).
    for cls in output_plugin_registry.GetAllPlugins():
      items.append(ApiOutputPluginDescriptorFromProtoClass(cls))

    items.sort(key=lambda item: item.name)
    return reflection_pb2.ApiListOutputPluginDescriptorsResult(items=items)
