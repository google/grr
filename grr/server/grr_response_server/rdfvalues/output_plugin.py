#!/usr/bin/env python
"""Output_plugin related rdf values."""
from __future__ import absolute_import
from __future__ import division

from __future__ import unicode_literals

import logging

from future.utils import python_2_unicode_compatible
from typing import Text

from grr_response_core.lib import registry
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import output_plugin_pb2


@python_2_unicode_compatible
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

  def __str__(self):
    result = self.plugin_name
    if self.plugin_args:
      result += " <%r>" % self.plugin_args
    return result
