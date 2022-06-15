#!/usr/bin/env python
"""Output_plugin related rdf values."""

import logging
from typing import Text
from typing import TypeVar

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import registry
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import output_plugin_pb2


_V = TypeVar("_V", bound=rdfvalue.RDFValue)


class OutputPluginDescriptor(rdf_structs.RDFProtoStruct):
  """An rdfvalue describing the output plugin to create."""

  protobuf = output_plugin_pb2.OutputPluginDescriptor

  def GetPluginClass(self):
    if self.plugin_name:
      plugin_cls = registry.OutputPluginRegistry.PluginClassByName(
          self.plugin_name)
      if plugin_cls is None:
        logging.warning("Unknown output plugin %s", self.plugin_name)
        return registry.OutputPluginRegistry.PluginClassByName(
            "UnknownOutputPlugin")

      return plugin_cls

  def GetPluginArgsClass(self):
    plugin_cls = self.GetPluginClass()
    if plugin_cls:
      return plugin_cls.args_type

  def GetPlugin(self):
    cls = registry.OutputPluginRegistry.PluginClassByName(self.plugin_name)
    return cls()

  # TODO: Remove this property.
  @property
  def plugin_args(self) -> _V:
    # Use new `args` field if available, else fallback to `plugin_args`.
    if self.HasField("args"):
      return self.args.Unpack(self.GetPluginArgsClass())

    return self.Get("plugin_args")

  @plugin_args.setter
  def plugin_args(self, value: bytes) -> None:
    self.Set("plugin_args", value)

  def __str__(self) -> Text:
    result = self.plugin_name
    if self.plugin_args:
      result += " <%r>" % self.plugin_args
    return result
