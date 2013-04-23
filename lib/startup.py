#!/usr/bin/env python
"""Startup routines for GRR.

Contains the startup routines and Init functions for initializing GRR.
"""

import logging
from grr.lib import config_lib
from grr.lib import registry


def ConfigInit():
  """Initialize the configuration manager."""
  try:
    # Check for a config init function in the local directory first.
    # pylint: disable=g-import-not-at-top
    from grr.lib.local import config as local_config
    local_config.ConfigLibInit()
    logging.debug("Using local ConfigLibInit from %s", local_config)
  except (AttributeError, ImportError):
    # If it doesn't exist load the default one.
    config_lib.ConfigLibInit()


# This method is only used in tests and will rerun all the hooks to create a
# clean state.
def TestInit():
  ConfigInit()
  registry.TestInit()


def Init():
  """Run all required startup routines and initialization hooks."""
  ConfigInit()
  registry.Init()
