#!/usr/bin/env python
"""Configuration parameters for the aff4 subsystem."""

from grr.lib import config_lib

config_lib.DEFINE_integer(
    "AFF4.cache_age", 5,
    "The number of seconds AFF4 objects live in the cache.")

config_lib.DEFINE_integer("AFF4.cache_max_size", 10000,
                          "Maximum size of the AFF4 objects cache.")

config_lib.DEFINE_integer(
    "AFF4.intermediate_cache_age", 600,
    "The number of seconds AFF4 urns live in index cache.")

config_lib.DEFINE_integer("AFF4.intermediate_cache_max_size", 2000,
                          "Maximum size of the AFF4 index cache.")

config_lib.DEFINE_string(
    "AFF4.change_email", None,
    "Email used by AFF4NotificationEmailListener to notify "
    "about AFF4 changes.")
