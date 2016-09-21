#!/usr/bin/env python
"""This plugin renders the client search page."""

from grr.lib import aff4
from grr.lib import flow
from grr.lib.aff4_objects import users as aff4_users


class SetGlobalNotification(flow.GRRGlobalFlow):
  """Updates user's global notification timestamp."""

  # This is an administrative flow.
  category = "/Administrative/"

  # Only admins can run this flow.
  AUTHORIZED_LABELS = ["admin"]

  # This flow is a SUID flow.
  ACL_ENFORCED = False

  args_type = aff4_users.GlobalNotification

  @flow.StateHandler()
  def Start(self):
    with aff4.FACTORY.Create(
        aff4_users.GlobalNotificationStorage.DEFAULT_PATH,
        aff4_type=aff4_users.GlobalNotificationStorage,
        mode="rw",
        token=self.token) as storage:
      storage.AddNotification(self.args)
