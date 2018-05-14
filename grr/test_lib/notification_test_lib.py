#!/usr/bin/env python
"""Test routines for user notifications-related testing."""

from grr.server.grr_response_server import aff4
from grr.server.grr_response_server import data_store
from grr.server.grr_response_server.aff4_objects import users as aff4_users


class NotificationTestMixin(object):
  """Test mixin for tests dealing with user notifications."""

  def GetUserNotifications(self, username):
    if data_store.RelationalDBReadEnabled():
      return data_store.REL_DB.ReadUserNotifications(username)
    else:
      fd = aff4.FACTORY.Open(
          "aff4:/users/%s" % username,
          aff4_type=aff4_users.GRRUser,
          token=self.token)
      return fd.ShowNotifications(reset=False)
