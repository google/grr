#!/usr/bin/env python
# Copyright 2011 Google Inc. All Rights Reserved.
"""AFF4 object representing grr users."""


import time

from grr.lib import aff4
from grr.lib import rdfvalue


class GRRUser(aff4.AFF4Object):
  """An AFF4 object modeling a GRR User."""

  class SchemaCls(aff4.AFF4Object.SchemaCls):
    PENDING_NOTIFICATIONS = aff4.Attribute(
        "aff4:notification/pending", rdfvalue.NotificationList,
        "The notifications pending for the user.", default="")

    SHOWN_NOTIFICATIONS = aff4.Attribute(
        "aff4:notifications/shown", rdfvalue.NotificationList,
        "Notifications already shown to the user.", default="")

  def Notify(self, message_type, subject, msg, source):
    """Send a notification to the user in the UI.

    Args:
      message_type: One of aff4_grr.Notification.notification_types e.g.
        "ViewObject", "HostInformation", "GrantAccess".
      subject: The subject to use, normally a URN.
      msg: The message to display.
      source: The class doing the notification.

    Raises:
      TypeError: On invalid message_type.
    """
    pending = self.Get(self.Schema.PENDING_NOTIFICATIONS)
    if message_type not in rdfvalue.Notification.notification_types:
      raise TypeError("Invalid notification type %s" % message_type)

    pending.Append(type=message_type, subject=subject, message=msg,
                   source=source, timestamp=long(time.time() * 1e6))

    # Limit the notification to 50, expiring older notifications.
    while len(pending) > 50:
      pending.Pop(0)

    self.Set(self.Schema.PENDING_NOTIFICATIONS, pending)

  def ShowNotifications(self, reset=True):
    """A generator of current notifications."""
    shown_notifications = self.Schema.SHOWN_NOTIFICATIONS()

    # Pending notifications first
    pending = self.Get(self.Schema.PENDING_NOTIFICATIONS)
    for notification in pending:
      shown_notifications.Append(notification)

    notifications = self.Get(self.Schema.SHOWN_NOTIFICATIONS)
    for notification in notifications:
      shown_notifications.Append(notification)

    # Shall we reset the pending notification state?
    if reset:
      self.Set(shown_notifications)
      self.Set(self.Schema.PENDING_NOTIFICATIONS())
      self.Flush()

    return shown_notifications
