#!/usr/bin/env python

from grr.lib import flags
from grr.lib import rdfvalue
from grr.server.grr_response_server import aff4
from grr.server.grr_response_server.aff4_objects import users
from grr.test_lib import acl_test_lib
from grr.test_lib import aff4_test_lib
from grr.test_lib import test_lib


class UsersTest(aff4_test_lib.AFF4ObjectTest, acl_test_lib.AclTestMixin):

  def setUp(self):
    super(UsersTest, self).setUp()

    self.user = aff4.FACTORY.Create(
        "aff4:/users/foo", aff4_type=users.GRRUser, mode="rw", token=self.token)
    self.user.Flush()

  def testNoNotificationIsReturnedIfItWasNotSet(self):
    self.assertFalse(self.user.GetPendingGlobalNotifications())

  def testNotificationIsReturnedWhenItIsSet(self):
    with aff4.FACTORY.Create(
        users.GlobalNotificationStorage.DEFAULT_PATH,
        aff4_type=users.GlobalNotificationStorage,
        mode="rw",
        token=self.token) as storage:
      storage.AddNotification(
          users.GlobalNotification(
              type=users.GlobalNotification.Type.ERROR,
              header="foo",
              content="bar",
              link="http://www.google.com"))

    notifications = self.user.GetPendingGlobalNotifications()
    self.assertTrue(notifications)
    self.assertEqual(len(notifications), 1)
    self.assertEqual(notifications[0].header, "foo")
    self.assertEqual(notifications[0].content, "bar")

  def testNotificationIsNotReturnedWhenItExpires(self):
    with test_lib.FakeTime(100):
      with aff4.FACTORY.Create(
          users.GlobalNotificationStorage.DEFAULT_PATH,
          aff4_type=users.GlobalNotificationStorage,
          mode="rw",
          token=self.token) as storage:
        storage.AddNotification(
            users.GlobalNotification(
                type=users.GlobalNotification.Type.ERROR,
                header="foo",
                content="bar",
                duration=rdfvalue.Duration("1h"),))

    with test_lib.FakeTime(101):
      notifications = self.user.GetPendingGlobalNotifications()
      self.assertTrue(notifications)

    with test_lib.FakeTime(100 + 3600 + 1):
      notifications = self.user.GetPendingGlobalNotifications()
      self.assertFalse(notifications)

  def testDescribe(self):
    self.user.AddLabels(["test1", "test2"])
    describe_str = self.user.Describe()
    self.assertTrue("test1" in describe_str)
    self.assertTrue("test2" in describe_str)


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
