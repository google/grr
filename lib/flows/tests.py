#!/usr/bin/env python
# Copyright 2011 Google Inc. All Rights Reserved.

"""Loads up all flow tests."""

# pylint: disable=unused-import
# These import populate the Flow test registry
from grr.lib.flows.console import debugging_test

# Cron tests.
from grr.lib.flows.cron import system_test

from grr.lib.flows.general import administrative_test
from grr.lib.flows.general import collectors_test
from grr.lib.flows.general import discovery_test
from grr.lib.flows.general import fetch_all_files_test
from grr.lib.flows.general import filesystem_test


from grr.lib.flows.general import find_test
from grr.lib.flows.general import fingerprint_test
from grr.lib.flows.general import grep_test
from grr.lib.flows.general import memory_test
from grr.lib.flows.general import network_test
from grr.lib.flows.general import processes_test
from grr.lib.flows.general import registry_test
from grr.lib.flows.general import services_test
from grr.lib.flows.general import timelines_test
from grr.lib.flows.general import transfer_test
from grr.lib.flows.general import utilities_test
from grr.lib.flows.general import webhistory_test
from grr.lib.flows.general import webplugin_test
from grr.lib.flows.general import windows_vsc_test

# Hunt tests.
from grr.lib.hunts import standard_test
