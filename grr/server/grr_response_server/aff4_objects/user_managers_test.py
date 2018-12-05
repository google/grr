#!/usr/bin/env python
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib import flags
from grr_response_core.lib import rdfvalue
from grr_response_server import access_control
from grr_response_server import aff4
from grr_response_server.aff4_objects import user_managers
from grr_response_server.aff4_objects import users
from grr.test_lib import acl_test_lib
from grr.test_lib import aff4_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib


class GRRUserTest(aff4_test_lib.AFF4ObjectTest):

  def testUserPasswords(self):
    with aff4.FACTORY.Create(
        "aff4:/users/test", users.GRRUser, token=self.token) as user:
      user.SetPassword("hello")

    user = aff4.FACTORY.Open(user.urn, token=self.token)

    self.assertFalse(user.CheckPassword("goodbye"))
    self.assertTrue(user.CheckPassword("hello"))

  def testLabels(self):
    with aff4.FACTORY.Create(
        "aff4:/users/test", users.GRRUser, token=self.token) as user:
      user.SetLabels(["hello", "world"], owner="GRR")

    user = aff4.FACTORY.Open(user.urn, token=self.token)
    self.assertListEqual(["hello", "world"], user.GetLabelsNames())

  def testBackwardsCompatibility(self):
    """Old GRR installations used crypt based passwords.

    Since crypt is not available on all platforms this has now been removed. We
    still support it on those platforms which have crypt. Backwards support
    means we can read and verify old crypt encoded passwords, but new passwords
    are encoded with sha256.
    """
    password = users.CryptedPassword()

    # This is crypt.crypt("hello", "ax")
    password._value = "axwHNtal/dlzU"

    self.assertFalse(password.CheckPassword("goodbye"))
    self.assertTrue(password.CheckPassword("hello"))


class CheckAccessHelperTest(test_lib.GRRBaseTest):

  def setUp(self):
    super(CheckAccessHelperTest, self).setUp()
    self.helper = user_managers.CheckAccessHelper("test")
    self.subject = rdfvalue.RDFURN("aff4:/some/path")

  def testReturnsFalseByDefault(self):
    self.assertRaises(access_control.UnauthorizedAccess,
                      self.helper.CheckAccess, self.subject, self.token)

  def testReturnsFalseOnFailedMatch(self):
    self.helper.Allow("aff4:/some/otherpath")
    self.assertRaises(access_control.UnauthorizedAccess,
                      self.helper.CheckAccess, self.subject, self.token)

  def testReturnsTrueOnMatch(self):
    self.helper.Allow("aff4:/some/path")
    self.assertTrue(self.helper.CheckAccess(self.subject, self.token))

  def testReturnsTrueIfOneMatchFails1(self):
    self.helper.Allow("aff4:/some/otherpath")
    self.helper.Allow("aff4:/some/path")
    self.assertTrue(self.helper.CheckAccess(self.subject, self.token))

  def testReturnsTrueIfOneMatchFails2(self):
    self.helper.Allow("aff4:/some/path")
    self.helper.Allow("aff4:/some/otherpath")
    self.assertTrue(self.helper.CheckAccess(self.subject, self.token))

  def testFnmatchFormatIsUsedByDefault1(self):
    self.helper.Allow("aff4:/some/*")
    self.assertTrue(self.helper.CheckAccess(self.subject, self.token))

  def testFnmatchFormatIsUsedByDefault2(self):
    self.helper.Allow("aff4:/some*")
    self.assertTrue(self.helper.CheckAccess(self.subject, self.token))

  def testFnmatchPatternCorrectlyMatchesFilesBelowDirectory(self):
    self.helper.Allow("aff4:/some/*")
    self.assertTrue(self.helper.CheckAccess(self.subject, self.token))
    self.assertRaises(
        access_control.UnauthorizedAccess, self.helper.CheckAccess,
        rdfvalue.RDFURN("aff4:/some"), self.token)

  def testCustomCheckWorksCorrectly(self):

    def CustomCheck(unused_subject, unused_token):
      return True

    self.helper.Allow("aff4:/some/path", CustomCheck)
    self.assertTrue(self.helper.CheckAccess(self.subject, self.token))

  def testCustomCheckFailsCorrectly(self):

    def CustomCheck(unused_subject, unused_token):
      raise access_control.UnauthorizedAccess("Problem")

    self.helper.Allow("aff4:/some/path", CustomCheck)
    self.assertRaises(access_control.UnauthorizedAccess,
                      self.helper.CheckAccess, self.subject, self.token)

  def testCustomCheckAcceptsAdditionalArguments(self):

    def CustomCheck(subject, unused_token, another_subject):
      if subject == another_subject:
        return True
      else:
        raise access_control.UnauthorizedAccess("Problem")

    self.helper.Allow("aff4:/*", CustomCheck, self.subject)
    self.assertRaises(access_control.UnauthorizedAccess,
                      self.helper.CheckAccess,
                      rdfvalue.RDFURN("aff4:/some/other/path"), self.token)
    self.assertTrue(self.helper.CheckAccess(self.subject, self.token))


class FullAccessControlManagerTest(test_lib.GRRBaseTest,
                                   acl_test_lib.AclTestMixin):
  """Unit tests for FullAccessControlManager."""

  def setUp(self):
    super(FullAccessControlManagerTest, self).setUp()
    self.access_manager = user_managers.FullAccessControlManager()

  def Ok(self, subject, access="r"):
    self.assertTrue(
        self.access_manager.CheckDataStoreAccess(self.token, [subject], access))

  def NotOk(self, subject, access="r"):
    self.assertRaises(access_control.UnauthorizedAccess,
                      self.access_manager.CheckDataStoreAccess, self.token,
                      [subject], access)

  def testReadSomePaths(self):
    """Tests some real world paths."""
    access = "r"

    self.Ok("aff4:/", access)
    self.Ok("aff4:/users", access)
    self.NotOk("aff4:/users/randomuser", access)

    self.Ok("aff4:/blobs", access)
    self.Ok("aff4:/blobs/12345678", access)

    self.Ok("aff4:/FP", access)
    self.Ok("aff4:/FP/12345678", access)

    self.Ok("aff4:/files", access)
    self.Ok("aff4:/files/12345678", access)

    self.Ok("aff4:/ACL", access)
    self.Ok("aff4:/ACL/randomuser", access)

    self.Ok("aff4:/stats", access)
    self.Ok("aff4:/stats/FileStoreStats", access)

    self.Ok("aff4:/config", access)
    self.Ok("aff4:/config/drivers", access)
    self.Ok("aff4:/config/drivers/windows/memory/winpmem.amd64.sys", access)

    self.Ok("aff4:/flows", access)
    self.Ok("aff4:/flows/F:12345678", access)

    self.Ok("aff4:/hunts", access)
    self.Ok("aff4:/hunts/H:12345678/C.1234567890123456", access)
    self.Ok("aff4:/hunts/H:12345678/C.1234567890123456/F:AAAAAAAA", access)

    self.Ok("aff4:/cron", access)
    self.Ok("aff4:/cron/OSBreakDown", access)

    self.Ok("aff4:/audit", access)
    self.Ok("aff4:/audit/log", access)
    self.Ok("aff4:/audit/logs", access)

    self.Ok("aff4:/C.0000000000000001", access)
    self.NotOk("aff4:/C.0000000000000001/fs/os", access)
    self.NotOk("aff4:/C.0000000000000001/flows/F:12345678", access)

  def testQuerySomePaths(self):
    """Tests some real world paths."""
    access = "rq"

    self.NotOk("aff4:/", access)
    self.NotOk("aff4:/users", access)
    self.NotOk("aff4:/users/randomuser", access)

    self.NotOk("aff4:/blobs", access)

    self.NotOk("aff4:/FP", access)

    self.NotOk("aff4:/files", access)
    self.Ok("aff4:/files/hash/generic/sha256/" + "a" * 64, access)

    self.Ok("aff4:/ACL", access)
    self.Ok("aff4:/ACL/randomuser", access)

    self.NotOk("aff4:/stats", access)

    self.Ok("aff4:/config", access)
    self.Ok("aff4:/config/drivers", access)
    self.Ok("aff4:/config/drivers/windows/memory/winpmem.amd64.sys", access)

    self.NotOk("aff4:/flows", access)
    self.Ok("aff4:/flows/W:12345678", access)

    self.Ok("aff4:/hunts", access)
    self.Ok("aff4:/hunts/H:12345678/C.1234567890123456", access)
    self.Ok("aff4:/hunts/H:12345678/C.1234567890123456/F:AAAAAAAA", access)

    self.Ok("aff4:/cron", access)
    self.Ok("aff4:/cron/OSBreakDown", access)

    self.NotOk("aff4:/audit", access)
    self.Ok("aff4:/audit/logs", access)

    self.Ok("aff4:/C.0000000000000001", access)
    self.NotOk("aff4:/C.0000000000000001/fs/os", access)
    self.NotOk("aff4:/C.0000000000000001/flows", access)

  def testSupervisorCanDoAnything(self):
    token = access_control.ACLToken(username="unknown", supervisor=True)

    self.assertTrue(
        self.access_manager.CheckClientAccess(token,
                                              "aff4:/C.0000000000000001"))
    self.assertTrue(
        self.access_manager.CheckHuntAccess(token, "aff4:/hunts/H:12344"))
    self.assertTrue(
        self.access_manager.CheckCronJobAccess(token, "aff4:/cron/blah"))
    self.assertTrue(self.access_manager.CheckIfCanStartFlow(token, "SomeFlow"))
    self.assertTrue(
        self.access_manager.CheckDataStoreAccess(
            token, ["aff4:/foo/bar"], requested_access="w"))

  def testEmptySubjectShouldRaise(self):
    token = access_control.ACLToken(username="unknown")

    with self.assertRaises(ValueError):
      self.access_manager.CheckClientAccess(token, "")

    with self.assertRaises(ValueError):
      self.access_manager.CheckHuntAccess(token, "")

    with self.assertRaises(ValueError):
      self.access_manager.CheckCronJobAccess(token, "")

    with self.assertRaises(ValueError):
      self.access_manager.CheckDataStoreAccess(
          token, [""], requested_access="r")

  def testCheckIfCanStartFlowReturnsTrueForClientFlowOnClient(self):
    self.assertTrue(
        self.access_manager.CheckIfCanStartFlow(
            self.token, flow_test_lib.ClientFlowWithCategory.__name__))

  def testCheckIfCanStartFlowRaisesForClientFlowWithoutCategoryOnClient(self):
    with self.assertRaises(access_control.UnauthorizedAccess):
      self.access_manager.CheckIfCanStartFlow(
          self.token, flow_test_lib.ClientFlowWithoutCategory.__name__)

  def testNoReasonShouldSearchForApprovals(self):
    token_without_reason = access_control.ACLToken(username="unknown")

    client_id = self.SetupClient(0)
    self.RequestAndGrantClientApproval(
        client_id, requestor="unknown", reason="I have one!")

    self.access_manager.CheckClientAccess(token_without_reason, client_id)
    # Check that token's reason got modified in the process:
    self.assertEqual(token_without_reason.reason, "I have one!")


class ValidateTokenTest(test_lib.GRRBaseTest):
  """Tests for ValidateToken()."""

  def testTokenWithUsernameAndReasonIsValid(self):
    token = access_control.ACLToken(username="test", reason="For testing")
    user_managers.ValidateToken(token, "aff4:/C.0000000000000001")

  def testNoneTokenIsNotValid(self):
    with self.assertRaises(access_control.UnauthorizedAccess):
      user_managers.ValidateToken(None, "aff4:/C.0000000000000001")

  def testTokenWithoutUsernameIsNotValid(self):
    token = access_control.ACLToken(reason="For testing")
    with self.assertRaises(access_control.UnauthorizedAccess):
      user_managers.ValidateToken(token, "aff4:/C.0000000000000001")


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
