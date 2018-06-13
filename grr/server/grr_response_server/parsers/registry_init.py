#!/usr/bin/env python
"""Loads all the parsers so they are visible in the registry."""

# pylint: disable=g-import-not-at-top
# pylint: disable=unused-import
from grr.lib.parsers import registry_init
from grr.server.grr_response_server.parsers import linux_cmd_parser
from grr.server.grr_response_server.parsers import linux_file_parser
from grr.server.grr_response_server.parsers import linux_pam_parser
from grr.server.grr_response_server.parsers import local
from grr.server.grr_response_server.parsers import rekall_artifact_parser
from grr.server.grr_response_server.parsers import windows_persistence
from grr.server.grr_response_server.parsers import windows_registry_parser
