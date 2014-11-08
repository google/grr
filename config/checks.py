#!/usr/bin/env python
"""Configuration parameters for the check subsystem."""

from grr.lib import config_lib

config_lib.DEFINE_integer("Checks.max_results", 50,
                          "Maximum items to include as check results.")

