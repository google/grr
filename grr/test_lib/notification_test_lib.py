#!/usr/bin/env python
"""Test routines for user notifications-related testing."""

from grr_response_server import data_store


class NotificationTestMixin(object):
  """Test mixin for tests dealing with user notifications."""

  def GetUserNotifications(self, username):
    return data_store.REL_DB.ReadUserNotifications(username)
