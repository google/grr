#!/usr/bin/env python
"""Module for InstantOutputPlugin registry."""

from typing import Dict, Type

from grr_response_server import instant_output_plugin


_INSTANT_OUTPUT_PLUGIN_PROTO_REGISTRY: Dict[
    str, Type[instant_output_plugin.InstantOutputPluginProto]
] = {}


def RegisterInstantOutputPluginProto(
    cls: Type[instant_output_plugin.InstantOutputPluginProto],
) -> None:
  """Registers an instant output plugin for protos."""
  if not cls.plugin_name:
    raise ValueError("Plugin must have a name.")
  _INSTANT_OUTPUT_PLUGIN_PROTO_REGISTRY[cls.plugin_name] = cls


def UnregisterInstantOutputPluginProto(plugin_name: str) -> None:
  """Unregisters an instant output plugin for protos."""
  del _INSTANT_OUTPUT_PLUGIN_PROTO_REGISTRY[plugin_name]


def GetPluginClassByNameProto(
    name: str,
) -> Type[instant_output_plugin.InstantOutputPluginProto]:
  """Returns plugin class for a given name for protos."""
  try:
    return _INSTANT_OUTPUT_PLUGIN_PROTO_REGISTRY[name]
  except KeyError:
    raise KeyError("No proto plugin with name '%s'." % name) from None
