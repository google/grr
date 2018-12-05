#!/usr/bin/env python
"""Load all flows so that they are visible in the registry."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

# pylint: disable=unused-import
# These imports populate the Flow registry
from grr_response_server.flows.general import administrative
from grr_response_server.flows.general import artifact_fallbacks
from grr_response_server.flows.general import audit

from grr_response_server.flows.general import ca_enroller
from grr_response_server.flows.general import checks
from grr_response_server.flows.general import collectors
from grr_response_server.flows.general import data_migration
from grr_response_server.flows.general import discovery

from grr_response_server.flows.general import export

from grr_response_server.flows.general import file_finder
from grr_response_server.flows.general import filesystem
from grr_response_server.flows.general import filetypes
from grr_response_server.flows.general import find
from grr_response_server.flows.general import fingerprint
from grr_response_server.flows.general import hardware

from grr_response_server.flows.general import memory
from grr_response_server.flows.general import network
from grr_response_server.flows.general import processes
from grr_response_server.flows.general import registry
from grr_response_server.flows.general import transfer
from grr_response_server.flows.general import webhistory
from grr_response_server.flows.general import windows_vsc
from grr_response_server.flows.general import yara_flows
