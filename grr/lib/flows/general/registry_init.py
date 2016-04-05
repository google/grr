#!/usr/bin/env python
"""Load all flows so that they are visible in the registry.
"""

# pylint: disable=unused-import
# These imports populate the Flow registry
from grr.lib.flows.general import administrative
from grr.lib.flows.general import aff4_notifiers
from grr.lib.flows.general import artifact_fallbacks
from grr.lib.flows.general import audit

from grr.lib.flows.general import ca_enroller
from grr.lib.flows.general import checks
from grr.lib.flows.general import collectors
from grr.lib.flows.general import discovery
from grr.lib.flows.general import dump_process_memory

from grr.lib.flows.general import export

from grr.lib.flows.general import file_finder
from grr.lib.flows.general import filesystem
from grr.lib.flows.general import filetypes
from grr.lib.flows.general import find
from grr.lib.flows.general import fingerprint
from grr.lib.flows.general import grep
from grr.lib.flows.general import hardware

from grr.lib.flows.general import memory
from grr.lib.flows.general import network
from grr.lib.flows.general import processes
from grr.lib.flows.general import registry
from grr.lib.flows.general import timelines
from grr.lib.flows.general import transfer
from grr.lib.flows.general import webhistory
from grr.lib.flows.general import windows_vsc

# This must be imported last to allow for all rdfvalues defined in flows to be
# imported first.
# pylint: disable=g-bad-import-order
from grr.lib.flows.general import endtoend
# pylint: enable=g-bad-import-order
