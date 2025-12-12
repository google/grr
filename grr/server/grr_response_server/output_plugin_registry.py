#!/usr/bin/env python
"""Module for OutputPluginProto registry."""

from typing import Dict, Type

from grr_response_server import output_plugin

_OUTPUT_PLUGIN_PROTO_REGISTRY: Dict[
    str, Type[output_plugin.OutputPluginProto]
] = {}


def RegisterOutputPluginProto(
    cls: Type[output_plugin.OutputPluginProto],
) -> None:
  """Registers an output plugin.

  Does not raise if the plugin is already registered. Rather it overrides the
  existing plugin with the newer one.

  Args:
    cls: The output plugin class to register.
  """
  _OUTPUT_PLUGIN_PROTO_REGISTRY[cls.__name__] = cls


def UnregisterOutputPluginProto(
    cls: Type[output_plugin.OutputPluginProto],
) -> None:
  """Unregisters an output plugin."""
  del _OUTPUT_PLUGIN_PROTO_REGISTRY[cls.__name__]


def GetPluginClassByName(
    name: str,
) -> Type[output_plugin.OutputPluginProto]:
  """Returns plugin class for a given name."""
  try:
    return _OUTPUT_PLUGIN_PROTO_REGISTRY[name]
  except KeyError:
    raise KeyError(f"No proto plugin with name '{name}'.") from None


def GetAllPlugins() -> list[Type[output_plugin.OutputPluginProto]]:
  """Returns all registered plugin classes."""
  return list(_OUTPUT_PLUGIN_PROTO_REGISTRY.values())
