#!/usr/bin/env python
"""This module contains windows specific client code."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_client.windows import regconfig
from grr_response_core.lib import config_parser


def RegisterPlugins():
  config_parser.RegisterParserClass("reg", regconfig.RegistryConfigParser)
