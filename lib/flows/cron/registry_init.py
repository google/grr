#!/usr/bin/env python
"""Load all cron flows in order to populate the registry.
"""

# pylint: disable=unused-import
# These imports populate the Flow registry
from grr.lib.flows.cron import compactors
from grr.lib.flows.cron import data_retention
from grr.lib.flows.cron import filestore_stats
from grr.lib.flows.cron import system
