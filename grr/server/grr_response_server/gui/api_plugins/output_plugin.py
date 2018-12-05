#!/usr/bin/env python
"""API handlers for dealing with output_plugins."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import itertools


from future.utils import iterkeys

from grr_response_core.lib.rdfvalues import protodict as rdf_protodict

from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto.api import output_plugin_pb2
from grr_response_proto.api import reflection_pb2
from grr_response_server import instant_output_plugin

from grr_response_server import output_plugin
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

  def InitFromOutputPluginClass(self, plugin_class):
    self.name = plugin_class.__name__
    self.description = plugin_class.description

    if issubclass(plugin_class, output_plugin.OutputPlugin):
      self.plugin_type = self.PluginType.LEGACY
      self.args_type = plugin_class.args_type.__name__
    elif issubclass(plugin_class, instant_output_plugin.InstantOutputPlugin):
      self.plugin_type = self.PluginType.INSTANT
      self.plugin_name = plugin_class.plugin_name
      self.friendly_name = plugin_class.friendly_name
    else:
      raise ValueError("Unknown plugin type: %s" % plugin_class)

    return self


class ApiListOutputPluginDescriptorsResult(rdf_structs.RDFProtoStruct):
  protobuf = reflection_pb2.ApiListOutputPluginDescriptorsResult
  rdf_deps = [
      ApiOutputPluginDescriptor,
  ]


class ApiListOutputPluginDescriptorsHandler(
    api_call_handler_base.ApiCallHandler):
  """Renders all available output plugins definitions."""

  result_type = ApiListOutputPluginDescriptorsResult

  def _GetPlugins(self, base_class):
    items = []
    for name in sorted(iterkeys(base_class.classes)):
      cls = base_class.classes[name]
      # While technically a valid plugin, UnknownOutputPlugin is only used as
      # a placeholder when unserializing old and now-deleted output plugins.
      # No need to display it in the UI.
      if cls == output_plugin.UnknownOutputPlugin:
        continue

      if cls.description:
        items.append(ApiOutputPluginDescriptor().InitFromOutputPluginClass(cls))

    return items

  def Handle(self, unused_args, token=None):
    result = ApiListOutputPluginDescriptorsResult()
    result.items = itertools.chain(
        self._GetPlugins(output_plugin.OutputPlugin),
        self._GetPlugins(instant_output_plugin.InstantOutputPlugin))
    return result
