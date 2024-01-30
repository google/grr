#!/usr/bin/env python
"""Test routines for user notifications-related testing."""

from grr_response_server import data_store
from grr_response_server.rdfvalues import mig_objects


class NotificationTestMixin(object):
  """Test mixin for tests dealing with user notifications."""

  def GetUserNotifications(self, username):
    notifications = data_store.REL_DB.ReadUserNotifications(username)
    return [mig_objects.ToRDFUserNotification(n) for n in notifications]
