#!/usr/bin/env python
"""Configuration parameters for the aff4 subsystem."""

from grr.lib import config_lib

config_lib.DEFINE_integer(
    "AFF4.cache_age", 5,
    "The number of seconds AFF4 objects live in the cache.")

config_lib.DEFINE_integer(
    "AFF4.notification_rules_cache_age", 60,
    "The number of seconds AFF4 notification rules are cached.")

config_lib.DEFINE_string(
    "AFF4.change_email", None,
    "Email used by AFF4NotificationEmailListener to notify "
    "about AFF4 changes.")
