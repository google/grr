#!/usr/bin/env python
"""GRR Rapid Response Framework."""


def version():
  # Delay imports until we have the config system to find the version.ini file.
  # pylint: disable=g-import-not-at-top
  import ConfigParser
  from grr.lib import config_lib

  config = ConfigParser.SafeConfigParser()
  config.read(config_lib.Resource().Filter("version.ini"))
  return dict(
      packageversion=config.get("Version", "packageversion"),
      major=config.getint("Version", "major"),
      minor=config.getint("Version", "minor"),
      revision=config.getint("Version", "revision"),
      release=config.getint("Version", "release"))
