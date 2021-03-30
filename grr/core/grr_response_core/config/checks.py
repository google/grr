#!/usr/bin/env python
"""Configuration parameters for the check subsystem."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib import config_lib

config_lib.DEFINE_list("Checks.config_dir", [
    "%(grr_response_server/checks@grr-response-server|resource)",
], "A list of directories to load checks from.")

config_lib.DEFINE_list("Checks.config_files", [],
                       "Paths of check configurations to load at start up.")

config_lib.DEFINE_integer("Checks.max_results", 50,
                          "Maximum items to include as check results.")
