#!/usr/bin/env python
"""Util for exporting data from GRR."""



import getpass

# pylint: disable=unused-import,g-bad-import-order
from grr.lib import server_plugins
# pylint: enable=unused-import,g-bad-import-order

from grr.lib import access_control
from grr.lib import config_lib
from grr.lib import data_store
from grr.lib import flags
from grr.lib import startup
from grr.tools import export_plugins

DESCRIPTION = "Tool for exporting data from GRR to the outside world."

flags.DEFINE_string("username", None,
                    "Username to use for export operations authorization.")

flags.DEFINE_string("reason", None,
                    "Reason to use for export operations authorization.")


def AddPluginsSubparsers():
  """Adds subparsers for all the registered export plugins.

  Classes inherited from ExportPlugin define subcommands that will be
  recognized by the export tool. For each of the plugins a subparser
  is created and then configured with ExportPlugin.ConfigurArgParser()
  call.
  """
  classes = sorted(export_plugins.plugin.ExportPlugin.classes.itervalues(),
                   key=lambda cls: cls.name)

  subparsers = flags.PARSER.add_subparsers(title="Subcommands")
  for cls in classes:
    if not cls.name:
      continue

    subparser = subparsers.add_parser(cls.name, help=cls.description)
    plugin_obj = cls()
    plugin_obj.ConfigureArgParser(subparser)

    # "func" attribute should be set to the plugin's Run() method
    subparser.set_defaults(func=plugin_obj.Run)


def main(unused_argv):
  """Main."""
  config_lib.CONFIG.AddContext("Commandline Context",
                               "Context applied for all command line tools")
  config_lib.CONFIG.AddContext("ExportTool Context",
                               "Context applied to the export tool.")
  startup.Init()

  data_store.default_token = access_control.ACLToken(
      username=flags.FLAGS.username or getpass.getuser(),
      reason=flags.FLAGS.reason)

  # If subcommand was specified by the user in the command line,
  # corresponding subparser should have initialized "func" argument
  # with a corresponding export plugin's Run() function.
  flags.FLAGS.func(flags.FLAGS)


if __name__ == "__main__":
  flags.PARSER.description = DESCRIPTION
  AddPluginsSubparsers()
  flags.StartMain(main)
