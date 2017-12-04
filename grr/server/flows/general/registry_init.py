#!/usr/bin/env python
"""Load all flows so that they are visible in the registry.
"""

# pylint: disable=unused-import
# These imports populate the Flow registry
from grr.server.flows.general import administrative
from grr.server.flows.general import artifact_fallbacks
from grr.server.flows.general import audit

from grr.server.flows.general import ca_enroller
from grr.server.flows.general import checks
from grr.server.flows.general import collectors
from grr.server.flows.general import discovery
from grr.server.flows.general import dump_process_memory

from grr.server.flows.general import export

from grr.server.flows.general import file_finder
from grr.server.flows.general import filesystem
from grr.server.flows.general import filetypes
from grr.server.flows.general import find
from grr.server.flows.general import fingerprint
from grr.server.flows.general import hardware

from grr.server.flows.general import memory
from grr.server.flows.general import network
from grr.server.flows.general import processes
from grr.server.flows.general import registry
from grr.server.flows.general import transfer
from grr.server.flows.general import webhistory
from grr.server.flows.general import windows_vsc
from grr.server.flows.general import yara_flows
