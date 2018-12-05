#!/usr/bin/env python
"""Tests for AuthorizationManager."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


from builtins import range  # pylint: disable=redefined-builtin

from grr_response_core.lib import flags
from grr_response_core.lib import utils
from grr_response_server.authorization import auth_manager
from grr_response_server.authorization import groups
from grr.test_lib import test_lib


class DummyAuthorization(object):
  """Dummy authorization object for test purposes."""

  def __init__(self, **kw_args):
    self.data = kw_args
    self.key = kw_args["router"]


class AuthorizationReaderTest(test_lib.GRRBaseTest):

  def setUp(self):
    super(AuthorizationReaderTest, self).setUp()
    self.auth_reader = auth_manager.AuthorizationReader()

  def testCreateAuthorizationsInitializesAuthorizationsFromYaml(self):
    yaml_data = """
router: "ApiCallRobotRouter"
users:
  - "foo"
  - "bar"
---
router: "ApiCallDisabledRouter"
users:
  - "blah"
"""
    self.auth_reader.CreateAuthorizations(yaml_data, DummyAuthorization)

    self.assertEqual(
        self.auth_reader.GetAuthorizationForSubject("ApiCallRobotRouter").data,
        dict(router="ApiCallRobotRouter", users=["foo", "bar"]))
    self.assertEqual(
        self.auth_reader.GetAuthorizationForSubject("ApiCallDisabledRouter")
        .data, dict(router="ApiCallDisabledRouter", users=["blah"]))

  def testCreateAuthorizationsRaisesOnDuplicateKeys(self):
    yaml_data = """
router: "ApiCallRobotRouter"
---
router: "ApiCallRobotRouter"
"""
    with self.assertRaises(auth_manager.InvalidAuthorization):
      self.auth_reader.CreateAuthorizations(yaml_data, DummyAuthorization)

  def testGetAllAuthorizationObjectsPreservesOrder(self):
    yaml_data = "---\n".join(["router: Router%d\n" % i for i in range(10)])

    self.auth_reader.CreateAuthorizations(yaml_data, DummyAuthorization)

    for index, authorization in enumerate(
        self.auth_reader.GetAllAuthorizationObjects()):
      self.assertEqual(authorization.key, "Router%d" % index)

  def testGetAuthSubjectsPreservesOrder(self):
    yaml_data = "---\n".join(["router: Router%d\n" % i for i in range(10)])

    self.auth_reader.CreateAuthorizations(yaml_data, DummyAuthorization)

    for index, subject in enumerate(self.auth_reader.GetAuthSubjects()):
      self.assertEqual(subject, "Router%d" % index)


class AuthorizationManagerTest(test_lib.GRRBaseTest):

  def setUp(self):
    super(AuthorizationManagerTest, self).setUp()

    self.group_access_manager = groups.NoGroupAccess()
    self.auth_manager = auth_manager.AuthorizationManager(
        group_access_manager=self.group_access_manager)

  def testGetAuthSubjectsPreservesOrder(self):
    for index in range(10):
      self.auth_manager.AuthorizeUser("foo", "subject_%d" % index)

    for index, subject in enumerate(self.auth_manager.GetAuthSubjects()):
      self.assertEqual(subject, "subject_%d" % index)

  def testCheckPermissionRaisesInvalidSubjectIfNoSubjectRegistered(self):
    with self.assertRaises(auth_manager.InvalidSubject):
      self.auth_manager.CheckPermissions("user-foo", "subject-bar")

  def testCheckPermissionsReturnsFalseIfDenyAllWasCalled(self):
    self.auth_manager.DenyAll("subject-bar")
    self.assertFalse(
        self.auth_manager.CheckPermissions("user-foo", "subject-bar"))

  def testCheckPermissionsReturnsTrueIfUserWasAuthorized(self):
    self.auth_manager.AuthorizeUser("user-foo", "subject-bar")
    self.assertTrue(
        self.auth_manager.CheckPermissions("user-foo", "subject-bar"))

  def testCheckPermissionsReturnsFalseIfUserWasNotAuthorized(self):
    self.auth_manager.AuthorizeUser("user-foo", "subject-bar")
    self.assertFalse(
        self.auth_manager.CheckPermissions("user-bar", "subject-bar"))

  def testCheckPermissionsReturnsTrueIfGroupWasAuthorized(self):
    self.auth_manager.DenyAll("subject-bar")
    with utils.Stubber(self.group_access_manager, "MemberOfAuthorizedGroup",
                       lambda *args: True):
      self.assertTrue(
          self.auth_manager.CheckPermissions("user-bar", "subject-bar"))

  def testCheckPermissionsReturnsFalseIfGroupWasNotAuthorized(self):
    self.auth_manager.DenyAll("subject-bar")

    with utils.Stubber(self.group_access_manager, "MemberOfAuthorizedGroup",
                       lambda *args: False):
      self.assertFalse(
          self.auth_manager.CheckPermissions("user-bar", "subject-bar"))


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
