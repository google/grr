#!/usr/bin/env python
"""This is the GRR client installer module.

GRR allows several installers to be registered as plugins. The
installers are executed when the client is deployed to a target system
in their specified order (according to the registry plugin system).

Installers are usually used to upgrade existing clients and setup
clients in unusual situations.
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import logging
import os
import sys

from absl import flags

from grr_response_core import config
from grr_response_core.config import contexts

if sys.platform == "darwin":
  from grr_response_client.osx import installers  # pylint: disable=g-import-not-at-top
elif sys.platform == "win32":
  from grr_response_client.windows import installers  # pylint: disable=g-import-not-at-top
else:
  installers = None


def RunInstaller():
  """Runs installers for the current platform."""

  try:
    os.makedirs(os.path.dirname(config.CONFIG["Installer.logfile"]))
  except OSError:
    pass

  # Always log to the installer logfile at debug level. This way if our
  # installer fails we can send detailed diagnostics.
  handler = logging.FileHandler(config.CONFIG["Installer.logfile"], mode="w")

  handler.setLevel(logging.DEBUG)

  # Add this to the root logger.
  logging.getLogger().addHandler(handler)

  # Ordinarily when the client starts up, the local volatile
  # configuration is read. Howevwer, when running the installer, we
  # need to ensure that only the installer configuration is used so
  # nothing gets overridden by local settings. We there must reload
  # the configuration from the flag and ignore the Config.writeback
  # location.
  config.CONFIG.Initialize(filename=flags.FLAGS.config, reset=True)
  config.CONFIG.AddContext(contexts.INSTALLER_CONTEXT,
                           "Context applied when we run the client installer.")

  if installers is None:
    logging.info("No installers found for %s.", sys.platform)
  else:
    logging.info("Starting installation procedure for GRR client.")
    installers.Run()
