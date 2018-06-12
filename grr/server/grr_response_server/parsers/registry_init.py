#!/usr/bin/env python
"""Loads all the parsers so they are visible in the registry."""

# pylint: disable=g-import-not-at-top
# pylint: disable=unused-import
from grr.server.grr_response_server.parsers import config_file
from grr.server.grr_response_server.parsers import cron_file_parser
from grr.server.grr_response_server.parsers import ie_history
from grr.server.grr_response_server.parsers import linux_cmd_parser
from grr.server.grr_response_server.parsers import linux_file_parser
from grr.server.grr_response_server.parsers import linux_pam_parser
from grr.server.grr_response_server.parsers import linux_release_parser
from grr.server.grr_response_server.parsers import linux_service_parser
from grr.server.grr_response_server.parsers import linux_sysctl_parser
from grr.server.grr_response_server.parsers import local
from grr.server.grr_response_server.parsers import osx_file_parser
from grr.server.grr_response_server.parsers import osx_launchd
from grr.server.grr_response_server.parsers import rekall_artifact_parser
from grr.server.grr_response_server.parsers import windows_persistence
from grr.server.grr_response_server.parsers import windows_registry_parser
from grr.server.grr_response_server.parsers import wmi_parser

try:
  from grr.server.grr_response_server.parsers import linux_software_parser
except ImportError:
  pass
