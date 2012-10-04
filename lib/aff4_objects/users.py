#!/usr/bin/env python

# Copyright 2011 Google Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""AFF4 object representing grr users."""


import time

from grr.lib import aff4
from grr.lib import utils
from grr.proto import jobs_pb2


class NotificationList(aff4.RDFProtoArray):
  """A List of notifications for this user."""
  _proto = jobs_pb2.Notification


class GRRUser(aff4.AFF4Object):
  """An AFF4 object modeling a GRR User."""

  class SchemaCls(aff4.AFF4Object.SchemaCls):
    PENDING_NOTIFICATIONS = aff4.Attribute(
        "aff4:notification/pending", NotificationList,
        "The notifications pending for the user.", default="")

    SHOWN_NOTIFICATIONS = aff4.Attribute(
        "aff4:notifications/shown", NotificationList,
        "Notifications already shown to the user.", default="")

  def Notify(self, message_type, subject, msg, source):
    """Send a notification to the user in the UI."""
    pending = self.Get(self.Schema.PENDING_NOTIFICATIONS)

    pending.Append(jobs_pb2.Notification(
        type=message_type, subject=utils.SmartUnicode(subject),
        message=utils.SmartUnicode(msg), source=source,
        timestamp=long(time.time() * 1e6)))

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
      shown_notifications.data.append(notification)

    notifications = self.Get(self.Schema.SHOWN_NOTIFICATIONS)
    for notification in notifications:
      shown_notifications.data.append(notification)

    # Shall we reset the pending notification state?
    if reset:
      self.Set(shown_notifications)
      self.Set(self.Schema.PENDING_NOTIFICATIONS())
      self.Flush()

    return shown_notifications.data
