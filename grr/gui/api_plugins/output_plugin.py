#!/usr/bin/env python
"""API handlers for dealing with output_plugins."""

from grr.gui import api_call_handler_base

from grr.lib import output_plugin
from grr.lib.rdfvalues import flows as rdf_flows
from grr.lib.rdfvalues import structs as rdf_structs

from grr.proto import api_pb2

CATEGORY = "Other"


class ApiOutputPluginsListHandler(api_call_handler_base.ApiCallHandler):
  """Renders all available output plugins definitions."""

  category = CATEGORY

  def Render(self, unused_args, token=None):
    result = {}
    for name in sorted(output_plugin.OutputPlugin.classes.keys()):
      cls = output_plugin.OutputPlugin.classes[name]
      if cls.description:
        result[name] = dict(name=name,
                            description=cls.description,
                            args_type=cls.args_type.__name__)

    return result


class ApiOutputPlugin(rdf_structs.RDFProtoStruct):
  """Output plugin API entity."""
  protobuf = api_pb2.ApiOutputPlugin

  def GetStateClass(self):
    return rdf_flows.FlowState
