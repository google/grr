#!/usr/bin/env python
"""Tests for root API user management calls."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from absl import app
from future.builtins import range

from grr_api_client import errors as grr_api_errors
from grr_api_client import root as grr_api_root
from grr_response_server import data_store
from grr_response_server.gui import api_integration_test_lib
from grr.test_lib import test_lib


class RootApiUserManagementTest(api_integration_test_lib.RootApiIntegrationTest
                               ):
  """E2E test for root API user management calls."""

  def _GetPassword(self, username):
    user = data_store.REL_DB.ReadGRRUser(username)
    return user.password if user.HasField("password") else None

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

    self.assertIsNone(self._GetPassword("user_foo"))

  def testStandardUserWithPasswordIsCorrectlyAdded(self):
    user = self.api.root.CreateGrrUser(username="user_foo", password="blah")
    self.assertEqual(user.username, "user_foo")
    self.assertEqual(user.data.username, "user_foo")
    self.assertEqual(user.data.user_type, user.USER_TYPE_STANDARD)

    password = self._GetPassword("user_foo")
    self.assertTrue(password.CheckPassword("blah"))

  def testUserModificationWorksCorrectly(self):
    user = self.api.root.CreateGrrUser(username="user_foo")
    self.assertEqual(user.data.user_type, user.USER_TYPE_STANDARD)

    user = user.Modify(user_type=user.USER_TYPE_ADMIN)
    self.assertEqual(user.data.user_type, user.USER_TYPE_ADMIN)

    user = user.Modify(user_type=user.USER_TYPE_STANDARD)
    self.assertEqual(user.data.user_type, user.USER_TYPE_STANDARD)

  def testUserPasswordCanBeModified(self):
    user = self.api.root.CreateGrrUser(username="user_foo", password="blah")

    password = self._GetPassword("user_foo")
    self.assertTrue(password.CheckPassword("blah"))

    user.Modify(password="ohno")

    password = self._GetPassword("user_foo")
    self.assertTrue(password.CheckPassword("ohno"))

  def testUsersAreCorrectlyListed(self):
    for i in range(10):
      self.api.root.CreateGrrUser(username="user_%d" % i)

    users = sorted(self.api.root.ListGrrUsers(), key=lambda u: u.username)

    # skip user that issues the request, which is implicitly created
    users = [u for u in users if u.username != self.token.username]

    self.assertLen(users, 10)
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
  app.run(main)
