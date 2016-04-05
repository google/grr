#!/usr/bin/env python
# Copyright 2012 Google Inc. All Rights Reserved.
"""Tests for the grr parsers."""

# These need to register plugins so, pylint: disable=unused-import
from grr.parsers import chrome_history_test
from grr.parsers import config_file_test
from grr.parsers import cron_file_parser_test
from grr.parsers import firefox3_history_test
from grr.parsers import ie_history_test
from grr.parsers import linux_cmd_parser_test
from grr.parsers import linux_file_parser_test
from grr.parsers import linux_release_parser_test
from grr.parsers import linux_service_parser_test
from grr.parsers import linux_sysctl_parser_test
from grr.parsers import osx_file_parser_test
from grr.parsers import osx_launchd_test
from grr.parsers import osx_quarantine_test
from grr.parsers import rekall_artifact_parser_test
from grr.parsers import sqlite_file_test
from grr.parsers import windows_persistence_test
from grr.parsers import windows_registry_parser_test
from grr.parsers import wmi_parser_test
# pylint: disable=g-import-not-at-top

try:
  from grr.parsers import linux_software_parser_test
except ImportError:
  pass
