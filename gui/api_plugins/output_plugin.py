#!/usr/bin/env python
"""API renderers for dealing with output_plugins."""

from grr.gui import api_call_renderers

from grr.lib import output_plugin


class ApiOutputPluginsListRenderer(api_call_renderers.ApiCallRenderer):
  """Renders all available output plugins definitions."""

  def Render(self, unused_args, token=None):
    result = {}
    for name in sorted(output_plugin.OutputPlugin.classes.keys()):
      cls = output_plugin.OutputPlugin.classes[name]
      if cls.description:
        result[name] = dict(name=name,
                            description=cls.description,
                            args_type=cls.args_type.__name__)

    return result
