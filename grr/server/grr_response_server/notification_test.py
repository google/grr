#!/usr/bin/env python
from absl import app

from grr_response_proto import objects_pb2
from grr_response_server import cronjobs
from grr_response_server import data_store
from grr_response_server import notification
from grr.test_lib import test_lib


class NotificationTest(test_lib.GRRBaseTest):

  def testNotifyDoesNotNotifySystemUsers(self):
    # Implicitly test that Notify does not throw Exception because system users
    # might not exist in the database.
    username = cronjobs.CRON_JOB_USERNAME

    notification.Notify(
        username,
        objects_pb2.UserNotification.Type.TYPE_CLIENT_INTERROGATED,
        "Fake discovery message",
        objects_pb2.ObjectReference(),
    )

    self.assertEmpty(data_store.REL_DB.ReadUserNotifications(username))


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
