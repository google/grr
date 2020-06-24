#!/usr/bin/env python
# Lint as: python3
"""Tests for Notifications."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from absl import app

from grr_response_server import cronjobs
from grr_response_server import data_store
from grr_response_server import notification
from grr_response_server.rdfvalues import objects as rdf_objects

from grr.test_lib import test_lib


class NotificationTest(test_lib.GRRBaseTest):

  def testNotifyDoesNotNotifySystemUsers(self):
    # Implicitly test that Notify does not throw Exception because system users
    # might not exist in the database.
    username = cronjobs.CRON_JOB_USERNAME

    notification.Notify(
        username, rdf_objects.UserNotification.Type.TYPE_CLIENT_INTERROGATED,
        "Fake discovery message", rdf_objects.ObjectReference())

    self.assertEmpty(data_store.REL_DB.ReadUserNotifications(username))


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
