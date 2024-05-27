#!/usr/bin/env python
"""A module for registering all known parsers."""

from grr_response_core.lib import parsers
from grr_response_core.lib.parsers import linux_release_parser


def Register():
  """Adds all known parsers to the registry."""
  # pyformat: disable

  # File multi-parsers.
  parsers.MULTI_FILE_PARSER_FACTORY.Register(
      "LinuxReleaseInfo", linux_release_parser.LinuxReleaseParser)

  # pyformat: enable
