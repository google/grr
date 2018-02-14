#!/usr/bin/env python
"""GRR library tests.

This module loads and registers all the GRR library tests.
"""

# These need to register plugins so, pylint: disable=unused-import
from grr_response_client import client_build_test
from grr_response_client import client_test
from grr_response_client import client_utils_test
from grr_response_client import client_vfs_test
from grr_response_client import comms_test
from grr_response_client.client_actions import tests
from grr_response_client.osx import objc_test
