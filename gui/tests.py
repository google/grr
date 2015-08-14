#!/usr/bin/env python
"""Register gui tests."""

# Registering tests so pylint: disable=unused-import
from grr.gui import api_aff4_object_renderers_test
from grr.gui import api_auth_manager_test
from grr.gui import api_value_renderers_test
from grr.gui import http_api_test
from grr.gui.api_plugins import tests
# pylint: enable=unused-import
