#!/usr/bin/env python
"""Python GRR API client library. Should be used for querying GRR API."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import os
import sys

try:
  import grr.proto  # pylint: disable=g-import-not-at-top
except ImportError:
  # Required for OpenSource standalone grr-api-client PIP package, so that it
  # can load protocol buffers compiled into Python files relative to
  # grr_api_client. See api_client/python/setup.py (compile_protos() function)
  # for details.
  sys.path.append(
      os.path.join(os.path.dirname(os.path.realpath(__file__)), "proto"))
