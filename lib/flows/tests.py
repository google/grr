#!/usr/bin/env python
"""Loads up all flow tests."""

# pylint: disable=unused-import
# These import populate the Flow test registry
from grr.lib.flows.console import debugging_test

# Cron tests.
from grr.lib.flows.cron import compactors_test
from grr.lib.flows.cron import filestore_stats_test
from grr.lib.flows.cron import system_test

from grr.lib.flows.general import administrative_test
from grr.lib.flows.general import artifact_fallbacks_test
from grr.lib.flows.general import audit_test
from grr.lib.flows.general import collectors_test
from grr.lib.flows.general import discovery_test
from grr.lib.flows.general import endtoend_test
from grr.lib.flows.general import export_test
from grr.lib.flows.general import file_finder_test
from grr.lib.flows.general import filesystem_test
from grr.lib.flows.general import filetypes_test
from grr.lib.flows.general import find_test
from grr.lib.flows.general import fingerprint_test
from grr.lib.flows.general import grep_test
from grr.lib.flows.general import memory_test
from grr.lib.flows.general import network_test
from grr.lib.flows.general import processes_test
from grr.lib.flows.general import registry_test
from grr.lib.flows.general import timelines_test
from grr.lib.flows.general import transfer_test
from grr.lib.flows.general import webhistory_test
from grr.lib.flows.general import webplugin_test
from grr.lib.flows.general import windows_vsc_test
