#!/usr/bin/env python
"""API handlers for dealing with output_plugins."""

from typing import Optional, Type, Union

from grr_response_core.lib import registry
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto.api import output_plugin_pb2
from grr_response_proto.api import reflection_pb2
from grr_response_server import instant_output_plugin
from grr_response_server import output_plugin
from grr_response_server.gui import api_call_context
from grr_response_server.gui import api_call_handler_base
from grr_response_server.rdfvalues import output_plugin as rdf_output_plugin


class ApiOutputPlugin(rdf_structs.RDFProtoStruct):
  """Output plugin API entity."""

  protobuf = output_plugin_pb2.ApiOutputPlugin
  rdf_deps = [
      rdf_output_plugin.OutputPluginDescriptor,
  ]

  def GetStateClass(self):
    return rdf_protodict.AttributedDict


class ApiOutputPluginDescriptor(rdf_structs.RDFProtoStruct):
  """Output plugin descriptor API entity."""

  protobuf = reflection_pb2.ApiOutputPluginDescriptor


def ApiOutputPluginDescriptorFromClass(
    plugin_class: Union[
        Type[output_plugin.OutputPlugin],
        Type[instant_output_plugin.InstantOutputPlugin],
    ],
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
  res.description = plugin_class.description

  if issubclass(plugin_class, output_plugin.OutputPlugin):
    res.plugin_type = reflection_pb2.ApiOutputPluginDescriptor.PluginType.LEGACY
    if plugin_class.args_type:
      res.args_type = plugin_class.args_type.__name__
  elif issubclass(plugin_class, instant_output_plugin.InstantOutputPlugin):
    res.plugin_type = (
        reflection_pb2.ApiOutputPluginDescriptor.PluginType.INSTANT
    )
    res.friendly_name = plugin_class.friendly_name
  else:
    raise ValueError("Unknown plugin type: %s" % plugin_class)

  return res


class ApiListOutputPluginDescriptorsResult(rdf_structs.RDFProtoStruct):
  protobuf = reflection_pb2.ApiListOutputPluginDescriptorsResult
  rdf_deps = [
      ApiOutputPluginDescriptor,
  ]


class ApiListOutputPluginDescriptorsHandler(
    api_call_handler_base.ApiCallHandler
):
  """Renders all available output plugins definitions."""

  result_type = ApiListOutputPluginDescriptorsResult
  proto_result_type = reflection_pb2.ApiListOutputPluginDescriptorsResult

  def Handle(
      self,
      unused_args: None,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> reflection_pb2.ApiListOutputPluginDescriptorsResult:
    items: list[reflection_pb2.ApiOutputPluginDescriptor] = []
    for cls in registry.OutputPluginRegistry.PLUGIN_REGISTRY.values():
      # While technically a valid plugin, UnknownOutputPlugin is only used as
      # a placeholder when unserializing old and now-deleted output plugins.
      # No need to display it in the UI.
      if cls == output_plugin.UnknownOutputPlugin:
        continue

      if cls.description:
        items.append(ApiOutputPluginDescriptorFromClass(cls))

    items.sort(key=lambda item: item.name)
    return reflection_pb2.ApiListOutputPluginDescriptorsResult(items=items)
