#!/usr/bin/env python
"""Tests for root API user management calls."""


from grr_api_client import errors as grr_api_errors
from grr_api_client import root as grr_api_root
from grr.lib import flags
from grr.server.grr_response_server import aff4
from grr.server.grr_response_server.gui import api_e2e_test_lib
from grr.test_lib import test_lib


class RootApiUserManagementTest(api_e2e_test_lib.RootApiE2ETest):
  """E2E test for root API user management calls."""

  def testStandardUserIsCorrectlyAdded(self):
    user = self.api.root.CreateGrrUser(username="user_foo")
    self.assertEqual(user.username, "user_foo")
    self.assertEqual(user.data.username, "user_foo")
    self.assertEqual(user.data.user_type, user.USER_TYPE_STANDARD)

  def testAdminUserIsCorrectlyAdded(self):
    user = self.api.root.CreateGrrUser(
        username="user_foo", user_type=grr_api_root.GrrUser.USER_TYPE_ADMIN)
    self.assertEqual(user.username, "user_foo")
    self.assertEqual(user.data.username, "user_foo")
    self.assertEqual(user.data.user_type, user.USER_TYPE_ADMIN)

    user_obj = aff4.FACTORY.Open("aff4:/users/user_foo", token=self.token)
    self.assertIsNone(user_obj.Get(user_obj.Schema.PASSWORD))

  def testStandardUserWithPasswordIsCorrectlyAdded(self):
    user = self.api.root.CreateGrrUser(username="user_foo", password="blah")
    self.assertEqual(user.username, "user_foo")
    self.assertEqual(user.data.username, "user_foo")
    self.assertEqual(user.data.user_type, user.USER_TYPE_STANDARD)

    user_obj = aff4.FACTORY.Open("aff4:/users/user_foo", token=self.token)
    self.assertTrue(
        user_obj.Get(user_obj.Schema.PASSWORD).CheckPassword("blah"))

  def testUserModificationWorksCorrectly(self):
    user = self.api.root.CreateGrrUser(username="user_foo")
    self.assertEqual(user.data.user_type, user.USER_TYPE_STANDARD)

    user = user.Modify(user_type=user.USER_TYPE_ADMIN)
    self.assertEqual(user.data.user_type, user.USER_TYPE_ADMIN)

    user = user.Modify(user_type=user.USER_TYPE_STANDARD)
    self.assertEqual(user.data.user_type, user.USER_TYPE_STANDARD)

  def testUserPasswordCanBeModified(self):
    user = self.api.root.CreateGrrUser(username="user_foo", password="blah")

    user_obj = aff4.FACTORY.Open("aff4:/users/user_foo", token=self.token)
    self.assertTrue(
        user_obj.Get(user_obj.Schema.PASSWORD).CheckPassword("blah"))

    user = user.Modify(password="ohno")

    user_obj = aff4.FACTORY.Open("aff4:/users/user_foo", token=self.token)
    self.assertTrue(
        user_obj.Get(user_obj.Schema.PASSWORD).CheckPassword("ohno"))

  def testUsersAreCorrectlyListed(self):
    for i in range(10):
      self.api.root.CreateGrrUser(username="user_%d" % i)

    users = sorted(self.api.root.ListGrrUsers(), key=lambda u: u.username)

    self.assertEqual(len(users), 10)
    for i, u in enumerate(users):
      self.assertEqual(u.username, "user_%d" % i)
      self.assertEqual(u.username, u.data.username)

  def testUserCanBeFetched(self):
    self.api.root.CreateGrrUser(
        username="user_foo", user_type=grr_api_root.GrrUser.USER_TYPE_ADMIN)

    user = self.api.root.GrrUser("user_foo").Get()
    self.assertEqual(user.username, "user_foo")
    self.assertEqual(user.data.user_type, grr_api_root.GrrUser.USER_TYPE_ADMIN)

  def testUserCanBeDeleted(self):
    self.api.root.CreateGrrUser(
        username="user_foo", user_type=grr_api_root.GrrUser.USER_TYPE_ADMIN)

    user = self.api.root.GrrUser("user_foo").Get()
    user.Delete()

    with self.assertRaises(grr_api_errors.ResourceNotFoundError):
      self.api.root.GrrUser("user_foo").Get()


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
