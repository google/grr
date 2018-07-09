#!/usr/bin/env python
"""Configuration parameters for the check subsystem."""
from grr.core.grr_response_core.lib import config_lib

config_lib.DEFINE_list("Checks.config_dir", [
    "%(grr.server.grr_response_server|module_path)/"
    "checks",
    "%(grr.server.grr_response_server|module_path)/"
    "checks/local"
], "A list of directories to load checks from.")

config_lib.DEFINE_list("Checks.config_files", [],
                       "Paths of check configurations to load at start up.")

config_lib.DEFINE_integer("Checks.max_results", 50,
                          "Maximum items to include as check results.")
