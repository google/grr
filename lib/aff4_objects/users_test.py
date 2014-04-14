#!/usr/bin/env python

# pylint: disable=unused-import,g-bad-import-order
from grr.lib import server_plugins
# pylint: enable=unused-import,g-bad-import-order

from grr.lib import aff4
from grr.lib import rdfvalue
from grr.lib import test_lib


class UsersTest(test_lib.GRRBaseTest):

  def setUp(self):
    super(UsersTest, self).setUp()

    self.user = aff4.FACTORY.Create("aff4:/users/foo",
                                    aff4_type="GRRUser",
                                    mode="rw",
                                    token=self.token)
    self.user.Flush()

  def testNoNotificationIsReturnedIfItWasNotSet(self):
    self.assertFalse(self.user.GetPendingGlobalNotifications())

  def testNotificationIsReturnedWhenItIsSet(self):
    with aff4.FACTORY.Create(aff4.GlobalNotificationStorage.DEFAULT_PATH,
                             aff4_type="GlobalNotificationStorage", mode="rw",
                             token=self.token) as storage:
      storage.AddNotification(rdfvalue.GlobalNotification(
          type=rdfvalue.GlobalNotification.Type.ERROR, header="foo",
          content="bar", link="http://www.google.com"))

    notifications = self.user.GetPendingGlobalNotifications()
    self.assertTrue(notifications)
    self.assertEqual(len(notifications), 1)
    self.assertEqual(notifications[0].header, "foo")
    self.assertEqual(notifications[0].content, "bar")

  def testNotificationIsNotReturnedWhenItExpires(self):
    with test_lib.FakeTime(100):
      with aff4.FACTORY.Create(aff4.GlobalNotificationStorage.DEFAULT_PATH,
                               aff4_type="GlobalNotificationStorage", mode="rw",
                               token=self.token) as storage:
        storage.AddNotification(rdfvalue.GlobalNotification(
            type=rdfvalue.GlobalNotification.Type.ERROR, header="foo",
            content="bar", duration=rdfvalue.Duration("1h"),))

    with test_lib.FakeTime(101):
      notifications = self.user.GetPendingGlobalNotifications()
      self.assertTrue(notifications)

    with test_lib.FakeTime(100 + 3600 + 1):
      notifications = self.user.GetPendingGlobalNotifications()
      self.assertFalse(notifications)
