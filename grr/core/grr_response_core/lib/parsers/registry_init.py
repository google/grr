#!/usr/bin/env python
"""Loads all the parsers so they are visible in the registry."""

# pylint: disable=g-import-not-at-top
# pylint: disable=unused-import
from grr_response_core.lib.parsers import config_file
from grr_response_core.lib.parsers import cron_file_parser
from grr_response_core.lib.parsers import ie_history
from grr_response_core.lib.parsers import linux_release_parser
from grr_response_core.lib.parsers import linux_service_parser
from grr_response_core.lib.parsers import linux_sysctl_parser
from grr_response_core.lib.parsers import osx_file_parser
from grr_response_core.lib.parsers import osx_launchd
from grr_response_core.lib.parsers import wmi_parser

try:
  from grr_response_core.lib.parsers import linux_software_parser
except ImportError:
  pass
