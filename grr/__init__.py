#!/usr/bin/env python
"""GRR Rapid Response Framework."""

import ConfigParser
import os


def version():
  """Return a dict with GRR version information."""
  # Delay import until we have the config system to find the version.ini file.
  # pylint: disable=g-import-not-at-top
  from grr.lib import config_lib

  version_ini = config_lib.Resource().Filter("version.ini")
  if not os.path.exists(version_ini):
    raise RuntimeError("Can't find version.ini at %s" % version_ini)

  config = ConfigParser.SafeConfigParser()
  config.read(version_ini)
  return dict(
      packageversion=config.get("Version", "packageversion"),
      major=config.getint("Version", "major"),
      minor=config.getint("Version", "minor"),
      revision=config.getint("Version", "revision"),
      release=config.getint("Version", "release"))
