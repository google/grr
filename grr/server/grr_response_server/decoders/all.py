#!/usr/bin/env python
"""A module for registering all known decoders."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_server import decoders


def Register():
  """Adds all known decoders to the registry."""
