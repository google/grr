#!/usr/bin/env python
"""End to end tests that run flows on actual clients."""

# lint: disable=unused-import
# These import populate the Flow registry
from grr.lib.flows.console.client_tests import administrative
from grr.lib.flows.console.client_tests import base
from grr.lib.flows.console.client_tests import collectors
from grr.lib.flows.console.client_tests import discovery
from grr.lib.flows.console.client_tests import file_finder
from grr.lib.flows.console.client_tests import filesystem
from grr.lib.flows.console.client_tests import fingerprint
from grr.lib.flows.console.client_tests import grep
from grr.lib.flows.console.client_tests import limits
from grr.lib.flows.console.client_tests import memory
from grr.lib.flows.console.client_tests import network
from grr.lib.flows.console.client_tests import processes
from grr.lib.flows.console.client_tests import registry
from grr.lib.flows.console.client_tests import transfer

