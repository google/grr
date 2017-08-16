#!/usr/bin/env python
"""Loads up all flow tests."""

# pylint: disable=unused-import
# These import populate the Flow test registry
from grr.server.flows.console import debugging_test

# Cron tests.
from grr.server.flows.cron import data_retention_test
from grr.server.flows.cron import filestore_stats_test
from grr.server.flows.cron import system_test

from grr.server.flows.general import administrative_test
from grr.server.flows.general import artifact_fallbacks_test
from grr.server.flows.general import audit_test
from grr.server.flows.general import checks_test
from grr.server.flows.general import collectors_artifact_downloader_test
from grr.server.flows.general import collectors_core_artifacts_test
from grr.server.flows.general import collectors_interactions_test
from grr.server.flows.general import collectors_test
from grr.server.flows.general import discovery_test
from grr.server.flows.general import endtoend_test
from grr.server.flows.general import file_finder_test
from grr.server.flows.general import filesystem_test
from grr.server.flows.general import filetypes_test
from grr.server.flows.general import find_test
from grr.server.flows.general import fingerprint_test
from grr.server.flows.general import grep_test
from grr.server.flows.general import hardware_test
from grr.server.flows.general import memory_test
from grr.server.flows.general import network_test
from grr.server.flows.general import processes_test
from grr.server.flows.general import registry_test
from grr.server.flows.general import transfer_test
from grr.server.flows.general import webhistory_test
from grr.server.flows.general import windows_vsc_test
