#!/usr/bin/env python
"""API config options."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib import config_lib
from grr_response_core.lib import rdfvalue

config_lib.DEFINE_integer("API.DailyFlowRequestLimit", "10",
                          "Number of flows a user can run on a single client "
                          "per day before being blocked by throttling. Set to "
                          "0 to disable checking.")

config_lib.DEFINE_semantic_value(
    rdfvalue.Duration,
    "API.FlowDuplicateInterval",
    default="1200s",
    help="Amount of time "
    "that needs to pass before the throttler will allow "
    "an identical flow to run on the same client. Set "
    "to 0s to disable checking.")

config_lib.DEFINE_string("API.RouterACLConfigFile", "",
                         "The file containing API acls, see "
                         "grr/config/api_acls.yaml for an example.")

config_lib.DEFINE_string("API.DefaultRouter", "DisabledApiCallRouter",
                         "The default router used by the API if there are no "
                         "rules defined in API.RouterACLConfigFile or if none "
                         "of these rules matches.")
