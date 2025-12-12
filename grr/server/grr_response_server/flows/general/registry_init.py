#!/usr/bin/env python
"""Load all flows so that they are visible in the registry."""

# pylint: disable=unused-import
# These imports populate the Flow registry
from grr_response_server.flows import file
from grr_response_server.flows.general import administrative
from grr_response_server.flows.general import collectors
from grr_response_server.flows.general import containers
from grr_response_server.flows.general import crowdstrike
from grr_response_server.flows.general import discovery
from grr_response_server.flows.general import dummy
from grr_response_server.flows.general import export
from grr_response_server.flows.general import file_finder
from grr_response_server.flows.general import filesystem
from grr_response_server.flows.general import hardware
from grr_response_server.flows.general import large_file
from grr_response_server.flows.general import memory
from grr_response_server.flows.general import memsize
from grr_response_server.flows.general import network
from grr_response_server.flows.general import osquery
from grr_response_server.flows.general import pipes
from grr_response_server.flows.general import processes
from grr_response_server.flows.general import read_low_level
from grr_response_server.flows.general import registry_finder
from grr_response_server.flows.general import services
from grr_response_server.flows.general import software
from grr_response_server.flows.general import timeline
from grr_response_server.flows.general import transfer
from grr_response_server.flows.general import webhistory
