#!/usr/bin/env python
"""Load all cron flows in order to populate the registry.
"""

# pylint: disable=unused-import
# These imports populate the Flow registry
from grr.server.grr_response_server.flows.cron import data_retention
from grr.server.grr_response_server.flows.cron import filestore_stats
from grr.server.grr_response_server.flows.cron import system
