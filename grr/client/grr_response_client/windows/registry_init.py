#!/usr/bin/env python
"""This module contains windows specific client code."""

from grr_response_client.windows import regconfig
from grr_response_core.lib import config_parser


def RegisterPlugins():
  config_parser.RegisterParserClass("reg", regconfig.RegistryConfigParser)
