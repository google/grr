#!/usr/bin/env python


import os

from grr.lib import access_control
from grr.lib import aff4
from grr.lib import config_lib
from grr.lib import data_store
from grr.lib import email_alerts
from grr.lib import flags
from grr.lib import flow
from grr.lib import hunts
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib import utils
from grr.lib.aff4_objects import aff4_grr
from grr.lib.aff4_objects import collects
from grr.lib.aff4_objects import security
from grr.lib.aff4_objects import user_managers
from grr.lib.aff4_objects import users
from grr.lib.authorization import client_approval_auth
from grr.lib.rdfvalues import aff4_rdfvalues
from grr.lib.rdfvalues import client as rdf_client


class GRRUserTest(test_lib.AFF4ObjectTest):

  def testUserPasswords(self):
    with aff4.FACTORY.Create("aff4:/users/test",
                             users.GRRUser,
                             token=self.token) as user:
      user.SetPassword("hello")

    user = aff4.FACTORY.Open(user.urn, token=self.token)

    self.assertFalse(user.CheckPassword("goodbye"))
    self.assertTrue(user.CheckPassword("hello"))

  def testLabels(self):
    with aff4.FACTORY.Create("aff4:/users/test",
                             users.GRRUser,
                             token=self.token) as user:
      user.SetLabels("hello", "world", owner="GRR")

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
    self.assertRaises(access_control.UnauthorizedAccess,
                      self.helper.CheckAccess, rdfvalue.RDFURN("aff4:/some"),
                      self.token)

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


class AdminOnlyFlow(flow.GRRFlow):
  AUTHORIZED_LABELS = ["admin"]

  # Flow has to have a category otherwise FullAccessControlManager won't
  # let non-supervisor users to run it at all (it will be considered
  # externally inaccessible).
  category = "/Test/"


class BasicAccessControlManagerTest(test_lib.GRRBaseTest):
  """Unit tests for FullAccessControlManager."""

  def setUp(self):
    super(BasicAccessControlManagerTest, self).setUp()
    self.access_manager = user_managers.BasicAccessControlManager()

  def testUserWithoutAuthorizedLabelsCanNotStartFlow(self):
    self.CreateUser("nonadmin")
    nonadmin_token = access_control.ACLToken(username="noadmin",
                                             reason="testing")

    with self.assertRaises(access_control.UnauthorizedAccess):
      self.access_manager.CheckIfCanStartFlow(nonadmin_token,
                                              AdminOnlyFlow.__name__,
                                              with_client_id=False)
    with self.assertRaises(access_control.UnauthorizedAccess):
      self.access_manager.CheckIfCanStartFlow(nonadmin_token,
                                              AdminOnlyFlow.__name__,
                                              with_client_id=True)

  def testUserWithAuthorizedLabelsCanStartFlow(self):
    self.CreateAdminUser("admin")
    admin_token = access_control.ACLToken(username="admin", reason="testing")

    self.access_manager.CheckIfCanStartFlow(admin_token,
                                            AdminOnlyFlow.__name__,
                                            with_client_id=False)
    self.access_manager.CheckIfCanStartFlow(admin_token,
                                            AdminOnlyFlow.__name__,
                                            with_client_id=True)


class FullAccessControlManagerTest(test_lib.GRRBaseTest):
  """Unit tests for FullAccessControlManager."""

  def setUp(self):
    super(FullAccessControlManagerTest, self).setUp()
    self.access_manager = user_managers.FullAccessControlManager()

  def Ok(self, subject, access="r"):
    self.assertTrue(self.access_manager.CheckDataStoreAccess(self.token,
                                                             [subject], access))

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

    self.Ok("aff4:/crashes", access)
    self.Ok("aff4:/crashes/Stream", access)

    self.Ok("aff4:/audit", access)
    self.Ok("aff4:/audit/log", access)
    self.Ok("aff4:/audit/logs", access)

    self.Ok("aff4:/C.0000000000000001", access)
    self.NotOk("aff4:/C.0000000000000001/fs/os", access)
    self.NotOk("aff4:/C.0000000000000001/flows/F:12345678", access)

    self.Ok("aff4:/tmp", access)
    self.Ok("aff4:/tmp/C8FAFC0F", access)

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

    self.NotOk("aff4:/crashes", access)

    self.NotOk("aff4:/audit", access)
    self.Ok("aff4:/audit/logs", access)

    self.Ok("aff4:/C.0000000000000001", access)
    self.NotOk("aff4:/C.0000000000000001/fs/os", access)
    self.NotOk("aff4:/C.0000000000000001/flows", access)

    self.NotOk("aff4:/tmp", access)

  def testSupervisorCanDoAnything(self):
    token = access_control.ACLToken(username="unknown", supervisor=True)

    self.assertTrue(self.access_manager.CheckClientAccess(
        token, "aff4:/C.0000000000000001"))
    self.assertTrue(self.access_manager.CheckHuntAccess(token,
                                                        "aff4:/hunts/H:12344"))
    self.assertTrue(self.access_manager.CheckCronJobAccess(token,
                                                           "aff4:/cron/blah"))
    self.assertTrue(self.access_manager.CheckIfCanStartFlow(
        token, "SomeFlow", with_client_id=True))
    self.assertTrue(self.access_manager.CheckIfCanStartFlow(
        token, "SomeFlow", with_client_id=False))
    self.assertTrue(self.access_manager.CheckDataStoreAccess(
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
      self.access_manager.CheckDataStoreAccess(token, [""],
                                               requested_access="r")

  def testCheckIfCanStartFlowReturnsTrueForClientFlowOnClient(self):
    self.assertTrue(self.access_manager.CheckIfCanStartFlow(
        self.token,
        ClientFlowWithCategory.__name__,
        with_client_id=True))

  def testCheckIfCanStartFlowRaisesForClientFlowWithoutCategoryOnClient(self):
    with self.assertRaises(access_control.UnauthorizedAccess):
      self.access_manager.CheckIfCanStartFlow(
          self.token,
          ClientFlowWithoutCategory.__name__,
          with_client_id=True)

  def testCheckIfCanStartFlowReturnsTrueForNotEnforcedFlowOnClient(self):
    self.assertTrue(self.access_manager.CheckIfCanStartFlow(
        self.token, NotEnforcedFlow.__name__,
        with_client_id=True))

  def testCheckIfCanStartFlowRaisesForClientFlowAsGlobal(self):
    with self.assertRaises(access_control.UnauthorizedAccess):
      self.access_manager.CheckIfCanStartFlow(self.token,
                                              ClientFlowWithCategory.__name__,
                                              with_client_id=False)

  def testCheckIfCanStartFlowRaisesForGlobalFlowWithoutCategoryAsGlobal(self):
    with self.assertRaises(access_control.UnauthorizedAccess):
      self.access_manager.CheckIfCanStartFlow(
          self.token,
          GlobalFlowWithoutCategory.__name__,
          with_client_id=False)

  def testCheckIfCanStartFlowReturnsTrueForGlobalFlowWithCategoryAsGlobal(self):
    self.assertTrue(self.access_manager.CheckIfCanStartFlow(
        self.token,
        GlobalFlowWithCategory.__name__,
        with_client_id=False))

  def testNoReasonShouldSearchForApprovals(self):
    token_without_reason = access_control.ACLToken(username="unknown")
    token_with_reason = access_control.ACLToken(username="unknown",
                                                reason="I have one!")

    client_id = "aff4:/C.0000000000000001"
    self.RequestAndGrantClientApproval(client_id, token=token_with_reason)

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


class ClientFlowWithoutCategory(flow.GRRFlow):
  pass


class ClientFlowWithCategory(flow.GRRFlow):
  category = "/Test/"


class NotEnforcedFlow(flow.GRRFlow):
  ACL_ENFORCED = False


class GlobalFlowWithoutCategory(flow.GRRGlobalFlow):
  pass


class GlobalFlowWithCategory(flow.GRRGlobalFlow):
  category = "/Test/"


class FullAccessControlManagerIntegrationTest(test_lib.GRRBaseTest):
  """Integration tests for FullAccessControlManager.

  This test differs from FullAccessControlManagerTest, as it doesn't call
  FullAccessControlManager's methods directly, but checks it through
  calls to GRR's functionality that has to check access via access control
  manager.
  """

  install_mock_acl = False

  def setUp(self):
    super(FullAccessControlManagerIntegrationTest, self).setUp()
    data_store.DB.security_manager = access_control.FullAccessControlManager()

  def ACLChecksDisabled(self):
    return test_lib.ACLChecksDisabledContextManager()

  def RevokeClientApproval(self, client_id, token, remove_from_cache=True):
    approval_urn = aff4.ROOT_URN.Add("ACL").Add(client_id).Add(
        token.username).Add(utils.EncodeReasonString(token.reason))

    with aff4.FACTORY.Open(approval_urn,
                           mode="rw",
                           token=self.token.SetUID()) as approval_request:
      approval_request.DeleteAttribute(approval_request.Schema.APPROVER)

    if remove_from_cache:
      data_store.DB.security_manager.acl_cache.ExpireObject(approval_urn)

  def CreateHuntApproval(self, hunt_urn, token, admin=False):
    approval_urn = aff4.ROOT_URN.Add("ACL").Add(hunt_urn.Path()).Add(
        token.username).Add(utils.EncodeReasonString(token.reason))

    with aff4.FACTORY.Create(approval_urn,
                             security.HuntApproval,
                             mode="rw",
                             token=self.token.SetUID()) as approval_request:
      approval_request.AddAttribute(approval_request.Schema.APPROVER(
          "Approver1"))
      approval_request.AddAttribute(approval_request.Schema.APPROVER(
          "Approver2"))

    if admin:
      self.CreateAdminUser("Approver1")

  def CreateSampleHunt(self):
    """Creats SampleHunt, writes it to the data store and returns it's id."""

    with hunts.GRRHunt.StartHunt(hunt_name="SampleHunt",
                                 token=self.token.SetUID()) as hunt:
      return hunt.session_id

  def testSimpleAccess(self):
    """Tests that simple access requires a token."""

    client_urn = rdf_client.ClientURN("C.%016X" % 0)

    # These should raise for a lack of token
    for urn, mode in [("aff4:/ACL", "r"), ("aff4:/config/drivers", "r"),
                      ("aff4:/", "rw"), (client_urn, "r")]:
      self.assertRaises(access_control.UnauthorizedAccess,
                        aff4.FACTORY.Open,
                        urn,
                        mode=mode)

    # These should raise for trying to get write access.
    for urn, mode in [("aff4:/ACL", "rw"), (client_urn, "rw")]:
      fd = aff4.FACTORY.Open(urn, mode=mode, token=self.token)
      # Force cache flush.
      fd._dirty = True
      self.assertRaises(access_control.UnauthorizedAccess, fd.Close)

    # These should raise for access without a token:
    for urn, mode in [(client_urn.Add("flows").Add("W:1234"), "r"),
                      (client_urn.Add("/fs"), "r")]:
      self.assertRaises(access_control.UnauthorizedAccess,
                        aff4.FACTORY.Open,
                        urn,
                        mode=mode)

      # Even if a token is provided - it is not authorized.
      self.assertRaises(access_control.UnauthorizedAccess,
                        aff4.FACTORY.Open,
                        urn,
                        mode=mode,
                        token=self.token)

  def testSupervisorToken(self):
    """Tests that the supervisor token overrides the approvals."""

    urn = rdf_client.ClientURN("C.%016X" % 0).Add("/fs/os/c")
    self.assertRaises(access_control.UnauthorizedAccess, aff4.FACTORY.Open, urn)

    super_token = access_control.ACLToken(username="test")
    super_token.supervisor = True
    aff4.FACTORY.Open(urn, mode="rw", token=super_token)

  def testExpiredTokens(self):
    """Tests that expired tokens are rejected."""

    urn = rdf_client.ClientURN("C.%016X" % 0).Add("/fs/os/c")
    self.assertRaises(access_control.UnauthorizedAccess, aff4.FACTORY.Open, urn)

    with test_lib.FakeTime(100):
      # Token expires in 5 seconds.
      super_token = access_control.ACLToken(username="test", expiry=105)
      super_token.supervisor = True

      # This should work since token is a super token.
      aff4.FACTORY.Open(urn, mode="rw", token=super_token)

    # Change the time to 200
    with test_lib.FakeTime(200):

      # Should be expired now.
      self.assertRaises(access_control.ExpiryError,
                        aff4.FACTORY.Open,
                        urn,
                        token=super_token,
                        mode="rw")

  def testApprovalExpiry(self):
    """Tests that approvals expire after the correct time."""

    client_id = "C.%016X" % 0
    urn = rdf_client.ClientURN(client_id).Add("/fs/os/c")
    token = access_control.ACLToken(username="test", reason="For testing")
    self.assertRaises(access_control.UnauthorizedAccess, aff4.FACTORY.Open, urn,
                      None, "rw", token)

    with test_lib.FakeTime(100.0, increment=1e-3):
      self.RequestAndGrantClientApproval(client_id, token)

      # This should work now.
      aff4.FACTORY.Open(urn, mode="rw", token=token)

    token_expiry = config_lib.CONFIG["ACL.token_expiry"]

    # This is close to expiry but should still work.
    with test_lib.FakeTime(100.0 + token_expiry - 100.0):
      aff4.FACTORY.Open(urn, mode="rw", token=token)

    # Past expiry, should fail.
    with test_lib.FakeTime(100.0 + token_expiry + 100.0):
      self.assertRaises(access_control.UnauthorizedAccess, aff4.FACTORY.Open,
                        urn, None, "rw", token)

  def testClientApproval(self):
    """Tests that we can create an approval object to access clients."""

    client_id = "C.%016X" % 0
    urn = rdf_client.ClientURN(client_id).Add("/fs")
    token = access_control.ACLToken(username="test", reason="For testing")

    self.assertRaises(access_control.UnauthorizedAccess,
                      aff4.FACTORY.Open,
                      urn,
                      None,
                      "rw",
                      token=token)

    self.RequestAndGrantClientApproval(client_id, token)

    fd = aff4.FACTORY.Open(urn, None, "rw", token=token)
    fd.Close()

    self.RevokeClientApproval(client_id, token)

    self.assertRaises(access_control.UnauthorizedAccess,
                      aff4.FACTORY.Open,
                      urn,
                      None,
                      "rw",
                      token=token)

  def testHuntApproval(self):
    """Tests that we can create an approval object to run hunts."""
    token = access_control.ACLToken(username="test", reason="For testing")
    hunt_urn = self.CreateSampleHunt()
    self.assertRaisesRegexp(access_control.UnauthorizedAccess,
                            "No approval found for",
                            flow.GRRFlow.StartFlow,
                            flow_name="StartHuntFlow",
                            token=token,
                            hunt_urn=hunt_urn)

    self.CreateHuntApproval(hunt_urn, token, admin=False)

    self.assertRaisesRegexp(
        access_control.UnauthorizedAccess,
        r"At least 1 approver\(s\) should have 'admin' label.",
        flow.GRRFlow.StartFlow,
        flow_name="StartHuntFlow",
        token=token,
        hunt_urn=hunt_urn)

    self.CreateHuntApproval(hunt_urn, token, admin=True)
    flow.GRRFlow.StartFlow(flow_name="StartHuntFlow",
                           token=token,
                           hunt_urn=hunt_urn)

  def testUserAccess(self):
    """Tests access to user objects."""
    token = access_control.ACLToken(username="test", reason="For testing")
    urn = aff4.ROOT_URN.Add("users")
    # We cannot open any user account.
    self.assertRaises(access_control.UnauthorizedAccess, aff4.FACTORY.Open,
                      urn.Add("some_user"), None, "rw", False, token)

    # But we can open our own.
    aff4.FACTORY.Open(urn.Add("test"), mode="rw", token=token)

    # And we can also access our labels.
    label_urn = urn.Add("test").Add("labels")
    labels = aff4.FACTORY.Open(label_urn, mode="rw", token=token)

    # But we cannot write to them.
    l = labels.Schema.LABELS()
    l.AddLabel(aff4_rdfvalues.AFF4ObjectLabel(name="admin", owner="GRR"))
    labels.Set(labels.Schema.LABELS, l)
    self.assertRaises(access_control.UnauthorizedAccess, labels.Close)

  def testForemanAccess(self):
    """Test admin users can access the foreman."""
    token = access_control.ACLToken(username="test", reason="For testing")
    self.assertRaises(access_control.UnauthorizedAccess,
                      aff4.FACTORY.Open,
                      "aff4:/foreman",
                      token=token)

    # We need a supervisor to manipulate a user's ACL token:
    super_token = access_control.ACLToken(username="test")
    super_token.supervisor = True

    # Make the user an admin user now, this time with the supervisor token.
    with aff4.FACTORY.Create("aff4:/users/test",
                             users.GRRUser,
                             token=super_token) as fd:

      fd.SetLabels("admin", owner="GRR")

    # Now we are allowed.
    aff4.FACTORY.Open("aff4:/foreman", token=token)

  def testCrashesAccess(self):
    # We need a supervisor to manipulate a user's ACL token:
    super_token = access_control.ACLToken(username="test")
    super_token.supervisor = True

    path = rdfvalue.RDFURN("aff4:/crashes")

    crashes = aff4.FACTORY.Create(path,
                                  collects.RDFValueCollection,
                                  token=self.token)
    self.assertRaises(access_control.UnauthorizedAccess, crashes.Close)

    # This shouldn't raise as we're using supervisor token.
    crashes = aff4.FACTORY.Create(path,
                                  collects.RDFValueCollection,
                                  token=super_token)
    crashes.Close()

    crashes = aff4.FACTORY.Open(path,
                                aff4_type=collects.RDFValueCollection,
                                mode="rw",
                                token=self.token)
    crashes.Set(crashes.Schema.DESCRIPTION("Some description"))
    self.assertRaises(access_control.UnauthorizedAccess, crashes.Close)

    crashes = aff4.FACTORY.Open(path,
                                aff4_type=collects.RDFValueCollection,
                                mode="r",
                                token=self.token)
    crashes.Close()

  def testFlowAccess(self):
    """Tests access to flows."""
    token = access_control.ACLToken(username="test", reason="For testing")
    client_id = "C." + "a" * 16

    self.assertRaises(access_control.UnauthorizedAccess,
                      flow.GRRFlow.StartFlow,
                      client_id=client_id,
                      flow_name=test_lib.SendingFlow.__name__,
                      message_count=1,
                      token=token)

    self.RequestAndGrantClientApproval(client_id, token)
    sid = flow.GRRFlow.StartFlow(client_id=client_id,
                                 flow_name=test_lib.SendingFlow.__name__,
                                 message_count=1,
                                 token=token)

    # Check we can open the flow object.
    flow_obj = aff4.FACTORY.Open(sid, mode="r", token=token)

    # Check that we can not write to it.
    flow_obj.mode = "rw"

    state = flow_obj.Get(flow_obj.Schema.FLOW_STATE)
    flow_obj.Set(state)

    # This is not allowed - Users can not write to flows.
    self.assertRaises(access_control.UnauthorizedAccess, flow_obj.Close)

    self.RevokeClientApproval(client_id, token)

    self.assertRaises(access_control.UnauthorizedAccess,
                      aff4.FACTORY.Open,
                      sid,
                      mode="r",
                      token=token)

    self.RequestAndGrantClientApproval(client_id, token)

    aff4.FACTORY.Open(sid, mode="r", token=token)

  def testCaches(self):
    """Makes sure that results are cached in the security manager."""

    token = access_control.ACLToken(username="test", reason="For testing")
    client_id = "C." + "b" * 16

    self.RequestAndGrantClientApproval(client_id, token)

    sid = flow.GRRFlow.StartFlow(client_id=client_id,
                                 flow_name=test_lib.SendingFlow.__name__,
                                 message_count=1,
                                 token=token)

    # Fill all the caches.
    aff4.FACTORY.Open(sid, mode="r", token=token)

    # Flush the AFF4 caches.
    aff4.FACTORY.Flush()

    # Remove the approval from the data store, but it should still exist in the
    # security manager cache.
    self.RevokeClientApproval(client_id, token, remove_from_cache=False)

    # If this doesn't raise now, all answers were cached.
    aff4.FACTORY.Open(sid, mode="r", token=token)

    # Flush the AFF4 caches.
    aff4.FACTORY.Flush()

    # Remove the approval from the data store, and from the security manager.
    self.RevokeClientApproval(client_id, token, remove_from_cache=True)

    # This must raise now.
    self.assertRaises(access_control.UnauthorizedAccess,
                      aff4.FACTORY.Open,
                      sid,
                      mode="r",
                      token=token)

  def testBreakGlass(self):
    """Test the breakglass mechanism."""
    client_id = rdf_client.ClientURN("C.%016X" % 0)
    urn = client_id.Add("/fs/os/c")

    self.assertRaises(access_control.UnauthorizedAccess,
                      aff4.FACTORY.Open,
                      urn,
                      token=self.token)

    # We expect to receive an email about this
    email = {}

    def SendEmail(to, from_user, subject, message, **_):
      email["to"] = to
      email["from_user"] = from_user
      email["subject"] = subject
      email["message"] = message

    with utils.Stubber(email_alerts.EMAIL_ALERTER, "SendEmail", SendEmail):
      flow.GRRFlow.StartFlow(client_id=client_id,
                             flow_name="BreakGlassGrantClientApprovalFlow",
                             token=self.token,
                             reason=self.token.reason)

      # Reset the emergency state of the token.
      self.token.is_emergency = False

      # This access is using the emergency_access granted, so we expect the
      # token to be tagged as such.
      aff4.FACTORY.Open(urn, token=self.token)

      self.assertEqual(email["to"],
                       config_lib.CONFIG["Monitoring.emergency_access_email"])
      self.assertIn(self.token.username, email["message"])
      self.assertEqual(email["from_user"], self.token.username)

    # Make sure the token is tagged as an emergency token:
    self.assertEqual(self.token.is_emergency, True)

  def testNonAdminsCanNotStartAdminOnlyFlow(self):
    noadmin_token = access_control.ACLToken(username="noadmin",
                                            reason="testing")
    with self.ACLChecksDisabled():
      client_id = self.SetupClients(1)[0]
      self.CreateUser("noadmin")
      self.RequestAndGrantClientApproval(client_id, token=noadmin_token)

    with self.assertRaises(access_control.UnauthorizedAccess):
      flow.GRRFlow.StartFlow(flow_name=AdminOnlyFlow.__name__,
                             client_id=client_id,
                             token=noadmin_token,
                             sync=False)

  def testAdminsCanStartAdminOnlyFlow(self):
    admin_token = access_control.ACLToken(username="adminuser",
                                          reason="testing")
    with self.ACLChecksDisabled():
      client_id = self.SetupClients(1)[0]
      self.CreateAdminUser("adminuser")
      self.RequestAndGrantClientApproval(client_id, token=admin_token)

    flow.GRRFlow.StartFlow(flow_name=AdminOnlyFlow.__name__,
                           client_id=client_id,
                           token=admin_token,
                           sync=False)

  def testNotAclEnforcedFlowCanBeStartedWithClient(self):
    with self.ACLChecksDisabled():
      client_id = self.SetupClients(1)[0]

    flow.GRRFlow.StartFlow(flow_name=NotEnforcedFlow.__name__,
                           client_id=client_id,
                           token=self.token,
                           sync=False)

  def testClientFlowWithoutCategoryCanNotBeStartedWithClient(self):
    with self.ACLChecksDisabled():
      client_id = self.SetupClients(1)[0]

    with self.assertRaises(access_control.UnauthorizedAccess):
      flow.GRRFlow.StartFlow(flow_name=ClientFlowWithoutCategory.__name__,
                             client_id=client_id,
                             token=self.token)

  def testClientFlowWithCategoryCanBeStartedWithClient(self):
    with self.ACLChecksDisabled():
      client_id = self.SetupClients(1)[0]
      self.RequestAndGrantClientApproval(client_id, self.token)

    flow.GRRFlow.StartFlow(flow_name=ClientFlowWithCategory.__name__,
                           client_id=client_id,
                           token=self.token,
                           sync=False)

  def testGlobalFlowWithoutCategoryCanNotBeStartedGlobally(self):
    with self.assertRaises(access_control.UnauthorizedAccess):
      flow.GRRFlow.StartFlow(flow_name=GlobalFlowWithoutCategory.__name__,
                             token=self.token,
                             sync=False)

  def testGlobalFlowWithCategoryCanBeStartedGlobally(self):
    flow.GRRFlow.StartFlow(flow_name=GlobalFlowWithCategory.__name__,
                           token=self.token,
                           sync=False)

  def testNotEnforcedFlowCanBeStartedGlobally(self):
    flow.GRRFlow.StartFlow(flow_name=NotEnforcedFlow.__name__,
                           token=self.token,
                           sync=False)


class ClientApprovalByLabelTests(test_lib.GRRBaseTest):
  """Integration tests for client approvals by label."""

  install_mock_acl = False

  def setUp(self):
    super(ClientApprovalByLabelTests, self).setUp()

    # Set up clients and labels before we turn on the FullACM. We need to create
    # the client because to check labels the client needs to exist.
    client_ids = self.SetupClients(3)
    self.client_nolabel = rdf_client.ClientURN(client_ids[0])
    self.client_legal = rdf_client.ClientURN(client_ids[1])
    self.client_prod = rdf_client.ClientURN(client_ids[2])
    with aff4.FACTORY.Open(self.client_legal,
                           aff4_type=aff4_grr.VFSGRRClient,
                           mode="rw",
                           token=self.token) as client_obj:
      client_obj.AddLabels("legal_approval")

    with aff4.FACTORY.Open(self.client_prod,
                           aff4_type=aff4_grr.VFSGRRClient,
                           mode="rw",
                           token=self.token) as client_obj:
      client_obj.AddLabels("legal_approval", "prod_admin_approval")

    self.db_manager_stubber = utils.Stubber(
        data_store.DB, "security_manager",
        access_control.FullAccessControlManager())
    self.db_manager_stubber.Start()

    self.approver = test_lib.ConfigOverrider(
        {"ACL.approvers_config_file": os.path.join(self.base_path,
                                                   "approvers.yaml")})
    self.approver.Start()

    # Get a fresh approval manager object and reload with test approvers.
    self.approval_manager_stubber = utils.Stubber(
        client_approval_auth, "CLIENT_APPROVAL_AUTH_MGR",
        client_approval_auth.ClientApprovalAuthorizationManager())
    self.approval_manager_stubber.Start()

  def tearDown(self):
    self.db_manager_stubber.Stop()
    self.approval_manager_stubber.Stop()
    self.approver.Stop()

  def testClientNoLabels(self):
    nolabel_urn = self.client_nolabel.Add("/fs")
    token = access_control.ACLToken(username="test", reason="For testing")

    self.assertRaises(access_control.UnauthorizedAccess,
                      aff4.FACTORY.Open,
                      nolabel_urn,
                      aff4_type=None,
                      mode="rw",
                      token=token)

    # approvers.yaml rules don't get checked because this client has no
    # labels. Regular approvals still required.
    self.RequestAndGrantClientApproval(self.client_nolabel, token)

    # Check we now have access
    with aff4.FACTORY.Open(nolabel_urn, aff4_type=None, mode="rw", token=token):
      pass

  def testClientApprovalSingleLabel(self):
    """Client requires an approval from a member of "legal_approval"."""
    legal_urn = self.client_legal.Add("/fs")
    token = access_control.ACLToken(username="test", reason="For testing")

    # No approvals yet, this should fail.
    self.assertRaises(access_control.UnauthorizedAccess,
                      aff4.FACTORY.Open,
                      legal_urn,
                      aff4_type=None,
                      mode="rw",
                      token=token)

    self.RequestAndGrantClientApproval(self.client_legal, token)
    # This approval isn't enough, we need one from legal, so it should still
    # fail.
    self.assertRaises(access_control.UnauthorizedAccess,
                      aff4.FACTORY.Open,
                      legal_urn,
                      aff4_type=None,
                      mode="rw",
                      token=token)

    # Grant an approval from a user in the legal_approval list in
    # approvers.yaml
    self.GrantClientApproval(self.client_legal,
                             token.username,
                             reason=token.reason,
                             approver="legal1")

    # Check we now have access
    with aff4.FACTORY.Open(legal_urn, aff4_type=None, mode="rw", token=token):
      pass

  def testClientApprovalMultiLabel(self):
    """Multi-label client approval test.

    This client requires one legal and two prod admin approvals. The requester
    must also be in the prod admin group.
    """
    prod_urn = self.client_prod.Add("/fs")
    token = access_control.ACLToken(username="prod1", reason="Some emergency")

    # No approvals yet, this should fail.
    self.assertRaises(access_control.UnauthorizedAccess,
                      aff4.FACTORY.Open,
                      prod_urn,
                      aff4_type=None,
                      mode="rw",
                      token=token)

    self.RequestAndGrantClientApproval(self.client_prod, token)

    # This approval from "approver" isn't enough.
    self.assertRaises(access_control.UnauthorizedAccess,
                      aff4.FACTORY.Open,
                      prod_urn,
                      aff4_type=None,
                      mode="rw",
                      token=token)

    # Grant an approval from a user in the legal_approval list in
    # approvers.yaml
    self.GrantClientApproval(self.client_prod,
                             token.username,
                             reason=token.reason,
                             approver="legal1")

    # We have "approver", "legal1": not enough.
    self.assertRaises(access_control.UnauthorizedAccess,
                      aff4.FACTORY.Open,
                      prod_urn,
                      aff4_type=None,
                      mode="rw",
                      token=token)

    # Grant an approval from a user in the prod_admin_approval list in
    # approvers.yaml
    self.GrantClientApproval(self.client_prod,
                             token.username,
                             reason=token.reason,
                             approver="prod2")

    # We have "approver", "legal1", "prod2": not enough.
    self.assertRaises(access_control.UnauthorizedAccess,
                      aff4.FACTORY.Open,
                      prod_urn,
                      aff4_type=None,
                      mode="rw",
                      token=token)

    self.GrantClientApproval(self.client_prod,
                             token.username,
                             reason=token.reason,
                             approver="prod3")

    # We have "approver", "legal1", "prod2", "prod3": we should have
    # access.
    with aff4.FACTORY.Open(prod_urn, aff4_type=None, mode="rw", token=token):
      pass

  def testClientApprovalMultiLabelCheckRequester(self):
    """Requester must be listed as prod_admin_approval in approvals.yaml."""
    prod_urn = self.client_prod.Add("/fs")
    token = access_control.ACLToken(username="notprod", reason="cheeky")

    # No approvals yet, this should fail.
    self.assertRaises(access_control.UnauthorizedAccess,
                      aff4.FACTORY.Open,
                      prod_urn,
                      aff4_type=None,
                      mode="rw",
                      token=token)

    # Grant all the necessary approvals
    self.RequestAndGrantClientApproval(self.client_prod, token)
    self.GrantClientApproval(self.client_prod,
                             token.username,
                             reason=token.reason,
                             approver="legal1")
    self.GrantClientApproval(self.client_prod,
                             token.username,
                             reason=token.reason,
                             approver="prod2")
    self.GrantClientApproval(self.client_prod,
                             token.username,
                             reason=token.reason,
                             approver="prod3")

    # We have "approver", "legal1", "prod2", "prod3" approvals but because
    # "notprod" user isn't in prod_admin_approval and
    # requester_must_be_authorized is True it should still fail. This user can
    # never get a complete approval.
    self.assertRaises(access_control.UnauthorizedAccess,
                      aff4.FACTORY.Open,
                      prod_urn,
                      aff4_type=None,
                      mode="rw",
                      token=token)


def main(argv):
  # Run the full test suite
  test_lib.GrrTestProgram(argv=argv)


if __name__ == "__main__":
  flags.StartMain(main)
