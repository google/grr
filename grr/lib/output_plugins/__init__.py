#!/usr/bin/env python
"""Output plugins implementations."""



from grr.lib import output_plugin

# pylint: disable=unused-import,g-import-not-at-top
try:
  from grr.lib.output_plugins import bigquery_plugin
except ImportError:
  pass

from grr.lib.output_plugins import csv_plugin
from grr.lib.output_plugins import email_plugin

# Add shortcuts to plugins into this module.
for name, cls in output_plugin.OutputPlugin.classes.items():
  globals()[name] = cls
