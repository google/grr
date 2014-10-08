#!/usr/bin/env python
"""Tests for the access control mechanisms."""


# pylint: disable=unused-import,g-bad-import-order
from grr.lib import server_plugins
# pylint: enable=unused-import,g-bad-import-order

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


class AccessControlTest(test_lib.GRRBaseTest):
  """Tests the access control mechanisms."""

  install_mock_acl = False

  def setUp(self):
    super(AccessControlTest, self).setUp()
    # We want to test the FullAccessControlManager
    data_store.DB.security_manager = access_control.FullAccessControlManager()

  def RevokeClientApproval(self, client_id, token, remove_from_cache=True):
    approval_urn = aff4.ROOT_URN.Add("ACL").Add(client_id).Add(
        token.username).Add(utils.EncodeReasonString(token.reason))

    super_token = access_control.ACLToken(username="test")
    super_token.supervisor = True

    approval_request = aff4.FACTORY.Open(approval_urn, mode="rw",
                                         token=super_token)
    approval_request.DeleteAttribute(approval_request.Schema.APPROVER)
    approval_request.Close()

    if remove_from_cache:
      data_store.DB.security_manager.acl_cache.ExpireObject(
          utils.SmartUnicode(approval_urn))

  def CreateHuntApproval(self, hunt_urn, token, admin=False):
    approval_urn = aff4.ROOT_URN.Add("ACL").Add(hunt_urn.Path()).Add(
        token.username).Add(utils.EncodeReasonString(token.reason))

    super_token = access_control.ACLToken(username="test")
    super_token.supervisor = True

    approval_request = aff4.FACTORY.Create(approval_urn, "HuntApproval",
                                           mode="rw", token=super_token)
    approval_request.AddAttribute(approval_request.Schema.APPROVER("Approver1"))
    approval_request.AddAttribute(approval_request.Schema.APPROVER("Approver2"))
    approval_request.Close()

    if admin:
      self.CreateAdminUser("Approver1")

  def CreateSampleHunt(self):
    """Creats SampleHunt, writes it to the data store and returns it's id."""

    super_token = access_control.ACLToken(username="test")
    super_token.supervisor = True

    with hunts.GRRHunt.StartHunt(
        hunt_name="SampleHunt", token=super_token) as hunt:
      return hunt.session_id

  def testSimpleAccess(self):
    """Tests that simple access requires a token."""

    client_urn = rdfvalue.ClientURN("C.%016X" % 0)

    # These should raise for a lack of token
    for urn, mode in [("aff4:/ACL", "r"),
                      ("aff4:/config/drivers", "r"),
                      ("aff4:/", "rw"),
                      (client_urn, "r")]:
      self.assertRaises(access_control.UnauthorizedAccess, aff4.FACTORY.Open,
                        urn, mode=mode)

    # These should raise for trying to get write access.
    for urn, mode in [("aff4:/ACL", "rw"),
                      (client_urn, "rw")]:
      fd = aff4.FACTORY.Open(urn, mode=mode, token=self.token)
      # Force cache flush.
      fd._dirty = True
      self.assertRaises(access_control.UnauthorizedAccess, fd.Close)

    # These should raise for access without a token:
    for urn, mode in [(client_urn.Add("flows").Add("W:1234"), "r"),
                      (client_urn.Add("/fs"), "r")]:
      self.assertRaises(access_control.UnauthorizedAccess, aff4.FACTORY.Open,
                        urn, mode=mode)

      # Even if a token is provided - it is not authorized.
      self.assertRaises(access_control.UnauthorizedAccess, aff4.FACTORY.Open,
                        urn, mode=mode, token=self.token)

  def testSupervisorToken(self):
    """Tests that the supervisor token overrides the approvals."""

    urn = rdfvalue.ClientURN("C.%016X" % 0).Add("/fs/os/c")
    self.assertRaises(access_control.UnauthorizedAccess, aff4.FACTORY.Open, urn)

    super_token = access_control.ACLToken(username="test")
    super_token.supervisor = True
    aff4.FACTORY.Open(urn, mode="rw", token=super_token)

  def testExpiredTokens(self):
    """Tests that expired tokens are rejected."""

    urn = rdfvalue.ClientURN("C.%016X" % 0).Add("/fs/os/c")
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
      self.assertRaises(access_control.ExpiryError, aff4.FACTORY.Open, urn,
                        token=super_token, mode="rw")

  def testApprovalExpiry(self):
    """Tests that approvals expire after the correct time."""

    client_id = "C.%016X" % 0
    urn = rdfvalue.ClientURN(client_id).Add("/fs/os/c")
    token = access_control.ACLToken(username="test", reason="For testing")
    self.assertRaises(access_control.UnauthorizedAccess, aff4.FACTORY.Open, urn,
                      None, "rw", token)

    with test_lib.FakeTime(100.0, increment=1e-3):
      self.GrantClientApproval(client_id, token)

      # This should work now.
      aff4.FACTORY.Open(urn, mode="rw", token=token)

    # 3 weeks later.
    with test_lib.FakeTime(100.0 + 3 * 7 * 24 * 60 * 60):
      # This should still work.
      aff4.FACTORY.Open(urn, mode="rw", token=token)

    # Getting close.
    with test_lib.FakeTime(100.0 + 4 * 7 * 24 * 60 * 60 - 100.0):
      # This should still work.
      aff4.FACTORY.Open(urn, mode="rw", token=token)

    # Over 4 weeks now.
    with test_lib.FakeTime(100.0 + 4 * 7 * 24 * 60 * 60 + 100.0):
      self.assertRaises(access_control.UnauthorizedAccess,
                        aff4.FACTORY.Open, urn, None, "rw", token)

  def testClientApproval(self):
    """Tests that we can create an approval object to access clients."""

    client_id = "C.%016X" % 0
    urn = rdfvalue.ClientURN(client_id).Add("/fs")
    token = access_control.ACLToken(username="test", reason="For testing")

    self.assertRaises(access_control.UnauthorizedAccess, aff4.FACTORY.Open, urn,
                      None, "rw", token=token)

    self.GrantClientApproval(client_id, token)

    fd = aff4.FACTORY.Open(urn, None, "rw", token=token)
    fd.Close()

    self.RevokeClientApproval(client_id, token)

    self.assertRaises(access_control.UnauthorizedAccess,
                      aff4.FACTORY.Open, urn, None, "rw", token=token)

  def testHuntApproval(self):
    """Tests that we can create an approval object to run hunts."""
    token = access_control.ACLToken(username="test", reason="For testing")
    hunt_urn = self.CreateSampleHunt()
    self.assertRaisesRegexp(
        access_control.UnauthorizedAccess,
        "No approval found for hunt",
        flow.GRRFlow.StartFlow,
        flow_name="StartHuntFlow", token=token, hunt_urn=hunt_urn)

    self.CreateHuntApproval(hunt_urn, token, admin=False)

    self.assertRaisesRegexp(
        access_control.UnauthorizedAccess,
        r"At least 1 approver\(s\) should have 'admin' label.",
        flow.GRRFlow.StartFlow,
        flow_name="StartHuntFlow", token=token, hunt_urn=hunt_urn)

    self.CreateHuntApproval(hunt_urn, token, admin=True)
    flow.GRRFlow.StartFlow(flow_name="StartHuntFlow", token=token,
                           hunt_urn=hunt_urn)

  def testUserAccess(self):
    """Tests access to user objects."""
    token = access_control.ACLToken(username="test", reason="For testing")
    urn = aff4.ROOT_URN.Add("users")
    # We cannot open any user account.
    self.assertRaises(access_control.UnauthorizedAccess,
                      aff4.FACTORY.Open, urn.Add("some_user"), None, "rw",
                      False, token)

    # But we can open our own.
    aff4.FACTORY.Open(urn.Add("test"), mode="rw", token=token)

    # And we can also access our labels.
    label_urn = urn.Add("test").Add("labels")
    labels = aff4.FACTORY.Open(label_urn, mode="rw", token=token)

    # But we cannot write to them.
    l = labels.Schema.LABELS()
    l.AddLabel(rdfvalue.AFF4ObjectLabel(name="admin", owner="GRR"))
    labels.Set(labels.Schema.LABELS, l)
    self.assertRaises(access_control.UnauthorizedAccess, labels.Close)

  def testForemanAccess(self):
    """Test admin users can access the foreman."""
    token = access_control.ACLToken(username="test", reason="For testing")
    self.assertRaises(access_control.UnauthorizedAccess,
                      aff4.FACTORY.Open, "aff4:/foreman", token=token)

    # We need a supervisor to manipulate a user's ACL token:
    super_token = access_control.ACLToken(username="test")
    super_token.supervisor = True

    # Make the user an admin user now, this time with the supervisor token.
    with aff4.FACTORY.Create("aff4:/users/test", "GRRUser",
                             token=super_token) as fd:

      fd.SetLabels("admin", owner="GRR")

    # Now we are allowed.
    aff4.FACTORY.Open("aff4:/foreman", token=token)

  def testCrashesAccess(self):
    # We need a supervisor to manipulate a user's ACL token:
    super_token = access_control.ACLToken(username="test")
    super_token.supervisor = True

    path = rdfvalue.RDFURN("aff4:/crashes")

    crashes = aff4.FACTORY.Create(path, "RDFValueCollection", token=self.token)
    self.assertRaises(access_control.UnauthorizedAccess, crashes.Close)

    # This shouldn't raise as we're using supervisor token.
    crashes = aff4.FACTORY.Create(path, "RDFValueCollection",
                                  token=super_token)
    crashes.Close()

    crashes = aff4.FACTORY.Open(path, aff4_type="RDFValueCollection",
                                mode="rw", token=self.token)
    crashes.Set(crashes.Schema.DESCRIPTION("Some description"))
    self.assertRaises(access_control.UnauthorizedAccess, crashes.Close)

    crashes = aff4.FACTORY.Open(path, aff4_type="RDFValueCollection",
                                mode="r", token=self.token)
    crashes.Close()

  def testFlowAccess(self):
    """Tests access to flows."""
    token = access_control.ACLToken(username="test", reason="For testing")
    client_id = "C." + "a" * 16

    self.assertRaises(access_control.UnauthorizedAccess, flow.GRRFlow.StartFlow,
                      client_id=client_id, flow_name="SendingFlow",
                      message_count=1, token=token)

    self.GrantClientApproval(client_id, token)
    sid = flow.GRRFlow.StartFlow(
        client_id=client_id, flow_name="SendingFlow", message_count=1,
        token=token)

    # Check we can open the flow object.
    flow_obj = aff4.FACTORY.Open(sid, mode="r", token=token)

    # Check that we can not write to it.
    flow_obj.mode = "rw"

    state = flow_obj.Get(flow_obj.Schema.FLOW_STATE)
    flow_obj.Set(state)

    # This is not allowed - Users can not write to flows.
    self.assertRaises(access_control.UnauthorizedAccess,
                      flow_obj.Close)

    self.RevokeClientApproval(client_id, token)

    self.assertRaises(access_control.UnauthorizedAccess,
                      aff4.FACTORY.Open, sid, mode="r", token=token)

    self.GrantClientApproval(client_id, token)

    aff4.FACTORY.Open(sid, mode="r", token=token)

  def testCaches(self):
    """Makes sure that results are cached in the security manager."""

    token = access_control.ACLToken(username="test", reason="For testing")
    client_id = "C." + "b" * 16

    self.GrantClientApproval(client_id, token)

    sid = flow.GRRFlow.StartFlow(
        client_id=client_id, flow_name="SendingFlow", message_count=1,
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
                      aff4.FACTORY.Open, sid, mode="r", token=token)

  def testBreakGlass(self):
    """Test the breakglass mechanism."""
    client_id = rdfvalue.ClientURN("C.%016X" % 0)
    urn = client_id.Add("/fs/os/c")

    self.assertRaises(access_control.UnauthorizedAccess, aff4.FACTORY.Open, urn,
                      token=self.token)

    # We expect to receive an email about this
    email = {}

    def SendEmail(to, from_user, subject, message, **_):
      email["to"] = to
      email["from_user"] = from_user
      email["subject"] = subject
      email["message"] = message

    with utils.Stubber(email_alerts, "SendEmail", SendEmail):
      flow.GRRFlow.StartFlow(
          client_id=client_id, flow_name="BreakGlassGrantClientApprovalFlow",
          token=self.token, reason=self.token.reason)

      # Reset the emergency state of the token.
      self.token.is_emergency = False

      # This access is using the emergency_access granted, so we expect the
      # token to be tagged as such.
      aff4.FACTORY.Open(urn, token=self.token)

      self.assertEqual(email["to"],
                       config_lib.CONFIG["Monitoring.emergency_access_email"])
      self.assert_(self.token.username in email["message"])
      self.assertEqual(email["from_user"], self.token.username)

    # Make sure the token is tagged as an emergency token:
    self.assertEqual(self.token.is_emergency, True)


class AccessControlTestLoader(test_lib.GRRTestLoader):
  base_class = AccessControlTest


def main(argv):
  # Run the full test suite
  test_lib.GrrTestProgram(argv=argv, testLoader=AccessControlTestLoader())

if __name__ == "__main__":
  flags.StartMain(main)
