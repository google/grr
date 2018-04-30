#!/usr/bin/env python
"""Additional (user-specific) UI logic."""

from grr.lib import registry


class LocalGuiInitHook(registry.InitHook):
  """User-specific init logic."""

  def RunOnce(self):
    pass
