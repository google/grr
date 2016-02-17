#!/usr/bin/env python
"""API config options."""

from grr.lib import config_lib
from grr.lib import rdfvalue

config_lib.DEFINE_list("API.access_groups", [],
                       "Groups allowed to call the AdminUI API. Empty list"
                       " means anyone can call. Note you MUST replace the "
                       "lib.authorizations.local.groups.GroupAccess class "
                       "with a class that can retrieve group information to"
                       " use this setting.")

config_lib.DEFINE_string("API.access_groups_label", "api_access",
                         "The access that API.access_groups will be granted. "
                         "This config option is useful if you have multiple "
                         "API servers which should be accessed by different "
                         "API.access_group groups. You likely don't want to "
                         "change this.")

config_lib.DEFINE_integer("API.DailyFlowRequestLimit", "10",
                          "Number of flows a user can run on a single client "
                          "per day before being blocked by throttling. Set to "
                          "0 to disable checking.")

config_lib.DEFINE_semantic(rdfvalue.Duration, "API.FlowDuplicateInterval",
                           default="1200s", description="Amount of time "
                           "that needs to pass before the throttler will allow "
                           "an identical flow to run on the same client. Set "
                           "to 0s to disable checking.")

config_lib.DEFINE_string("API.HandlerACLFile", "",
                         "The file containing API acls, see "
                         "grr/config/api_acls.yaml for an example.")
