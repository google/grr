#!/usr/bin/env python
"""Configuration parameters for the configuration subsystem."""

from grr.lib import config_lib

config_lib.DEFINE_string("Config.writeback", "",
                         "Location for writing back the configuration.")
