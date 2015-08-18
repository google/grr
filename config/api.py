#!/usr/bin/env python
"""API config options."""

from grr.lib import config_lib
from grr.lib import rdfvalue

config_lib.DEFINE_string("API.AuthorizationManager",
                         "SimpleAPIAuthorizationManager",
                         "API Authorization manager class to be used")

config_lib.DEFINE_integer("API.DailyFlowRequestLimit", "10",
                          "Number of flows a user can run on a single client "
                          "per day before being blocked by throttling. Set to "
                          "0 to disable checking.")

config_lib.DEFINE_semantic(rdfvalue.Duration, "API.FlowDuplicateInterval",
                           default="1200s", description="Amount of time "
                           "that needs to pass before the throttler will allow "
                           "an identical flow to run on the same client. Set "
                           "to 0s to disable checking.")

config_lib.DEFINE_string("API.RendererACLFile", "",
                         "The file containing API acls, see "
                         "grr/config/api_acls.yaml for an example.")

