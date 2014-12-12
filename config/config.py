#!/usr/bin/env python
"""Configuration parameters for the configuration subsystem."""

from grr.lib import config_lib

config_lib.DEFINE_string("Config.directory", "/etc/grr",
                         "Directory for grr server config files.")

config_lib.DEFINE_string("Config.writeback", "",
                         "Location for writing back the configuration.")

config_lib.DEFINE_string("ConfigUpdater.old_config", None,
                         "Path to a previous config file, imported during"
                         " config_updater.Initialize.")
