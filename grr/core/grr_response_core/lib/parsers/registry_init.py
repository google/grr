#!/usr/bin/env python
"""Loads all the parsers so they are visible in the registry."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

# pylint: disable=g-import-not-at-top
# pylint: disable=unused-import
from grr_response_core.lib.parsers import config_file
from grr_response_core.lib.parsers import cron_file_parser
from grr_response_core.lib.parsers import ie_history
from grr_response_core.lib.parsers import linux_cmd_parser
from grr_response_core.lib.parsers import linux_file_parser
from grr_response_core.lib.parsers import linux_pam_parser
from grr_response_core.lib.parsers import linux_release_parser
from grr_response_core.lib.parsers import linux_service_parser
from grr_response_core.lib.parsers import linux_sysctl_parser
from grr_response_core.lib.parsers import local
from grr_response_core.lib.parsers import osx_file_parser
from grr_response_core.lib.parsers import osx_launchd
from grr_response_core.lib.parsers import rekall_artifact_parser
from grr_response_core.lib.parsers import windows_persistence
from grr_response_core.lib.parsers import windows_registry_parser
from grr_response_core.lib.parsers import wmi_parser


try:
  # TODO(hanuszczak): Why is it imported conditionally? Is it possible to avoid
  # that?
  from grr_response_core.lib.parsers import linux_software_parser
except ImportError:
  pass
