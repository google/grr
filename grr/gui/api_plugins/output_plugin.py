#!/usr/bin/env python
"""API handlers for dealing with output_plugins."""

from grr.gui import api_call_handler_base

from grr.lib import output_plugin
from grr.lib.rdfvalues import protodict as rdf_protodict
from grr.lib.rdfvalues import structs as rdf_structs

from grr.proto import api_pb2


class ApiOutputPlugin(rdf_structs.RDFProtoStruct):
  """Output plugin API entity."""
  protobuf = api_pb2.ApiOutputPlugin

  def GetStateClass(self):
    return rdf_protodict.AttributedDict


class ApiOutputPluginDescriptor(rdf_structs.RDFProtoStruct):
  """Output plugin descriptor API entity."""
  protobuf = api_pb2.ApiOutputPluginDescriptor

  def InitFromOutputPluginClass(self, plugin_class):
    self.name = plugin_class.__name__
    self.description = plugin_class.description
    self.args_type = plugin_class.args_type.__name__
    return self


class ApiListOutputPluginDescriptorsResult(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiListOutputPluginDescriptorsResult


class ApiListOutputPluginDescriptorsHandler(
    api_call_handler_base.ApiCallHandler):
  """Renders all available output plugins definitions."""

  result_type = ApiListOutputPluginDescriptorsResult

  def Handle(self, unused_args, token=None):
    result = ApiListOutputPluginDescriptorsResult()
    for name in sorted(output_plugin.OutputPlugin.classes.keys()):
      cls = output_plugin.OutputPlugin.classes[name]
      if cls.description:
        result.items.append(ApiOutputPluginDescriptor()
                            .InitFromOutputPluginClass(cls))

    return result
