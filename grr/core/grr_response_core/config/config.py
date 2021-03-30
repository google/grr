#!/usr/bin/env python
"""Configuration parameters for the configuration subsystem."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib import config_lib

config_lib.DEFINE_string("Config.prefix",
                         "%(grr_response_core@grr-response-core|resource)",
                         "Prefix directory for general file storage.")

config_lib.DEFINE_string("Config.directory",
                         "%(install_data/etc@grr-response-core|resource)",
                         "Directory for grr server config files.")

config_lib.DEFINE_string("Config.writeback",
                         "%(Config.directory)/server.local.yaml",
                         "Location for writing back the configuration.")

config_lib.DEFINE_string(
    "ConfigUpdater.old_config", None,
    "Path to a previous config file, imported during"
    " config_updater.Initialize.")
