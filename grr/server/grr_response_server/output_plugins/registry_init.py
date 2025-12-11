#!/usr/bin/env python
"""Register all available output plugins."""

from grr_response_server import instant_output_plugin_registry
from grr_response_server import output_plugin_registry
from grr_response_server.instant_output_plugins import csv_instant_plugin
from grr_response_server.instant_output_plugins import sqlite_instant_plugin
from grr_response_server.instant_output_plugins import yaml_instant_plugin
from grr_response_server.output_plugins import email_plugin


def RegisterInstantOutputPlugins():
  """Registers all instant output plugins."""
  instant_output_plugin_registry.RegisterInstantOutputPluginProto(
      csv_instant_plugin.CSVInstantOutputPluginProto
  )
  instant_output_plugin_registry.RegisterInstantOutputPluginProto(
      sqlite_instant_plugin.SqliteInstantOutputPluginProto
  )
  instant_output_plugin_registry.RegisterInstantOutputPluginProto(
      yaml_instant_plugin.YamlInstantOutputPluginProto
  )


def RegisterOutputPluginProtos():
  """Registers all output plugins."""
  output_plugin_registry.RegisterOutputPluginProto(
      email_plugin.EmailOutputPlugin
  )
