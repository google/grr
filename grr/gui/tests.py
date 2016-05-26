#!/usr/bin/env python
"""Register gui tests."""

# Registering tests so pylint: disable=unused-import
from grr.gui import api_auth_manager_test
from grr.gui import api_call_handler_utils_test
from grr.gui import api_call_router_test
from grr.gui import api_call_router_with_approval_checks_test
from grr.gui import api_call_router_without_checks_test
from grr.gui import api_labels_restricted_call_router_test
from grr.gui import api_value_renderers_test
from grr.gui import http_api_test
from grr.gui.api_plugins import tests
# pylint: enable=unused-import
