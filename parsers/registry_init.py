#!/usr/bin/env python
"""Loads all the parsers so they are visible in the registry."""

# pylint: disable=g-import-not-at-top
# pylint: disable=unused-import
from grr.parsers import config_file
from grr.parsers import cron_file_parser
from grr.parsers import ie_history
from grr.parsers import linux_cmd_parser
from grr.parsers import linux_file_parser
from grr.parsers import linux_pam_parser
from grr.parsers import linux_release_parser
from grr.parsers import linux_service_parser
from grr.parsers import linux_sysctl_parser
from grr.parsers import local
from grr.parsers import osx_file_parser
from grr.parsers import osx_launchd
from grr.parsers import rekall_artifact_parser
from grr.parsers import windows_persistence
from grr.parsers import windows_registry_parser
from grr.parsers import wmi_parser

try:
  from grr.parsers import linux_software_parser
except ImportError:
  pass
