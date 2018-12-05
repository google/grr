#!/usr/bin/env python
"""Additional (user-specific) UI logic."""
from __future__ import absolute_import
from __future__ import division

from grr.core.grr_response_server.lib import registry


class LocalGuiInitHook(registry.InitHook):
  """User-specific init logic."""

  def RunOnce(self):
    pass
