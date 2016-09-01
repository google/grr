#!/usr/bin/env python
"""This module contains tests for user API handlers."""



from grr.gui import api_test_lib
from grr.gui.api_plugins import user as user_plugin

from grr.lib import access_control
from grr.lib import aff4
from grr.lib import email_alerts
from grr.lib import flags
from grr.lib import flow
from grr.lib import hunts
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib import utils

from grr.lib.aff4_objects import cronjobs as aff4_cronjobs
from grr.lib.aff4_objects import security as aff4_security
from grr.lib.aff4_objects import users as aff4_users

from grr.lib.flows.general import administrative

from grr.lib.hunts import standard
from grr.lib.hunts import standard_test


class ApiCreateApprovalHandlerTestMixin(object):
  """Base class for tests testing Create*ApprovalHandlers."""

  APPROVAL_TYPE = None

  def SetUpApprovalTest(self):
    self.CreateUser("test")
    self.CreateUser("approver")

    self.handler = None
    self.args = None
    self.subject_urn = None

    if not self.APPROVAL_TYPE:
      raise ValueError("APPROVAL_TYPE has to be set.")

  def testCreatesAnApprovalWithGivenAttributes(self):
    result = self.handler.Handle(self.args, token=self.token)
    approval_urn = aff4.ROOT_URN.Add("ACL").Add(self.subject_urn.Path()).Add(
        self.token.username).Add(result.id)

    fd = aff4.FACTORY.Open(
        approval_urn,
        aff4_type=self.APPROVAL_TYPE,
        age=aff4.ALL_TIMES,
        token=self.token)
    self.assertEqual(fd.Get(fd.Schema.SUBJECT), self.subject_urn)
    self.assertEqual(fd.Get(fd.Schema.REASON), self.token.reason)
    self.assertEqual(fd.GetNonExpiredApprovers(), [self.token.username])
    self.assertEqual(fd.Get(fd.Schema.EMAIL_CC), "approver,test@example.com")

  def testApproversFromArgsAreIgnored(self):
    # It shouldn't be possible to specify list of approvers when creating
    # an approval. List of approvers contains names of GRR users who
    # approved the approval.
    self.args.approval.approvers = [self.token.username, "approver"]

    result = self.handler.Handle(self.args, token=self.token)
    approval_urn = aff4.ROOT_URN.Add("ACL").Add(self.subject_urn.Path()).Add(
        self.token.username).Add(result.id)

    fd = aff4.FACTORY.Open(
        approval_urn,
        aff4_type=self.APPROVAL_TYPE,
        age=aff4.ALL_TIMES,
        token=self.token)
    self.assertEqual(fd.GetNonExpiredApprovers(), [self.token.username])

  def testRaisesOnEmptyReason(self):
    self.args.approval.reason = ""

    with self.assertRaises(ValueError):
      self.handler.Handle(self.args, token=self.token)

  def testNotifiesGrrUsers(self):
    self.handler.Handle(self.args, token=self.token)

    fd = aff4.FACTORY.Open(
        "aff4:/users/approver", aff4_type=aff4_users.GRRUser, token=self.token)
    notifications = fd.ShowNotifications(reset=False)

    self.assertEqual(len(notifications), 1)

  def testSendsEmailsToGrrUsersAndCcAddresses(self):
    addresses = []

    def SendEmailStub(to_user,
                      from_user,
                      unused_subject,
                      unused_message,
                      cc_addresses=None,
                      **unused_kwargs):
      addresses.append((to_user, from_user, cc_addresses))

    with utils.Stubber(email_alerts.EMAIL_ALERTER, "SendEmail", SendEmailStub):
      self.handler.Handle(self.args, token=self.token)

    self.assertEqual(len(addresses), 1)
    self.assertEqual(addresses[0], ("approver", "test", "test@example.com"))


class ApiGetClientApprovalHandlerTest(test_lib.GRRBaseTest):
  """Test for ApiGetClientApprovalHandler."""

  def setUp(self):
    super(ApiGetClientApprovalHandlerTest, self).setUp()
    self.client_id = self.SetupClients(1)[0]
    self.handler = user_plugin.ApiGetClientApprovalHandler()

  def testRendersRequestedClientApproval(self):
    flow_urn = flow.GRRFlow.StartFlow(
        client_id=self.client_id,
        flow_name="RequestClientApprovalFlow",
        reason="blah",
        subject_urn=self.client_id,
        approver="approver",
        email_cc_address="test@example.com",
        token=self.token)
    flow_fd = aff4.FACTORY.Open(
        flow_urn, aff4_type=flow.GRRFlow, token=self.token)
    approval_id = flow_fd.state.approval_id

    args = user_plugin.ApiGetClientApprovalArgs(
        client_id=self.client_id,
        approval_id=approval_id,
        username=self.token.username)
    result = self.handler.Handle(args, token=self.token)

    self.assertEqual(result.subject.urn, self.client_id)
    self.assertEqual(result.reason, "blah")
    self.assertEqual(result.is_valid, False)
    self.assertEqual(result.is_valid_message,
                     "Requires 2 approvers for access.")

    self.assertEqual(result.notified_users, ["approver"])
    self.assertEqual(result.email_cc_addresses, ["test@example.com"])

    # Every approval is self-approved by default.
    self.assertEqual(result.approvers, [self.token.username])

  def testIncludesApproversInResultWhenApprovalIsGranted(self):
    flow_urn = flow.GRRFlow.StartFlow(
        client_id=self.client_id,
        flow_name="RequestClientApprovalFlow",
        reason="blah",
        subject_urn=self.client_id,
        approver="approver",
        token=self.token)
    flow_fd = aff4.FACTORY.Open(
        flow_urn, aff4_type=flow.GRRFlow, token=self.token)
    approval_id = flow_fd.state.approval_id

    approver_token = access_control.ACLToken(username="approver")
    flow.GRRFlow.StartFlow(
        client_id=self.client_id,
        flow_name="GrantClientApprovalFlow",
        reason="blah",
        delegate=self.token.username,
        subject_urn=self.client_id,
        token=approver_token)

    args = user_plugin.ApiGetClientApprovalArgs(
        client_id=self.client_id,
        approval_id=approval_id,
        username=self.token.username)
    result = self.handler.Handle(args, token=self.token)

    self.assertTrue(result.is_valid)
    self.assertEqual(
        sorted(result.approvers),
        sorted([approver_token.username, self.token.username]))

  def testRaisesWhenApprovalIsNotFound(self):
    args = user_plugin.ApiGetClientApprovalArgs(
        client_id=self.client_id,
        approval_id="approval:112233",
        username=self.token.username)

    # TODO(user): throw some standard exception that can be converted to
    # HTTP 404 status code.
    with self.assertRaises(IOError):
      self.handler.Handle(args, token=self.token)


class ApiGetClientApprovalHandlerRegressionTest(
    api_test_lib.ApiCallHandlerRegressionTest):
  """Regression test for ApiGetClientApprovalHandler."""

  handler = "ApiGetClientApprovalHandler"

  def Run(self):
    with test_lib.FakeTime(42):
      self.CreateAdminUser("approver")

      clients = self.SetupClients(2)
      for client_id in clients:
        # Delete the certificate as it's being regenerated every time the
        # client is created.
        with aff4.FACTORY.Open(
            client_id, mode="rw", token=self.token) as grr_client:
          grr_client.DeleteAttribute(grr_client.Schema.CERT)

    with test_lib.FakeTime(44):
      flow_urn = flow.GRRFlow.StartFlow(
          client_id=clients[0],
          flow_name="RequestClientApprovalFlow",
          reason="foo",
          subject_urn=clients[0],
          approver="approver",
          token=self.token)
      flow_fd = aff4.FACTORY.Open(
          flow_urn, aff4_type=flow.GRRFlow, token=self.token)
      approval1_id = flow_fd.state.approval_id

    with test_lib.FakeTime(45):
      flow_urn = flow.GRRFlow.StartFlow(
          client_id=clients[1],
          flow_name="RequestClientApprovalFlow",
          reason="bar",
          subject_urn=clients[1],
          approver="approver",
          token=self.token)
      flow_fd = aff4.FACTORY.Open(
          flow_urn, aff4_type=flow.GRRFlow, token=self.token)
      approval2_id = flow_fd.state.approval_id

    with test_lib.FakeTime(84):
      approver_token = access_control.ACLToken(username="approver")
      flow.GRRFlow.StartFlow(
          client_id=clients[1],
          flow_name="GrantClientApprovalFlow",
          reason="bar",
          delegate=self.token.username,
          subject_urn=clients[1],
          token=approver_token)

    with test_lib.FakeTime(126):
      self.Check(
          "GET",
          "/api/users/test/approvals/client/%s/%s" %
          (clients[0].Basename(), approval1_id),
          replace={approval1_id: "approval:111111"})
      self.Check(
          "GET",
          "/api/users/test/approvals/client/%s/%s" %
          (clients[1].Basename(), approval2_id),
          replace={approval2_id: "approval:222222"})


class ApiGrantClientApprovalHandlerRegressionTest(
    api_test_lib.ApiCallHandlerRegressionTest):
  """Regression test for ApiGrantClientApprovalHandler."""

  handler = "ApiGrantClientApprovalHandler"

  def Run(self):
    with test_lib.FakeTime(42):
      self.CreateAdminUser("requestor")

      clients = self.SetupClients(1)
      for client_id in clients:
        # Delete the certificate as it's being regenerated every time the
        # client is created.
        with aff4.FACTORY.Open(
            client_id, mode="rw", token=self.token) as grr_client:
          grr_client.DeleteAttribute(grr_client.Schema.CERT)

    with test_lib.FakeTime(44):
      requestor_token = access_control.ACLToken(username="requestor")
      flow_urn = flow.GRRFlow.StartFlow(
          client_id=clients[0],
          flow_name="RequestClientApprovalFlow",
          reason="foo",
          subject_urn=clients[0],
          approver=self.token.username,
          token=requestor_token)
      flow_fd = aff4.FACTORY.Open(
          flow_urn, aff4_type=flow.GRRFlow, token=self.token)
      approval_id = flow_fd.state.approval_id

    with test_lib.FakeTime(126):
      self.Check(
          "POST",
          "/api/users/requestor/approvals/client/%s/%s/actions/grant" %
          (clients[0].Basename(), approval_id),
          replace={approval_id: "approval:111111"})


class ApiCreateClientApprovalHandlerTest(test_lib.GRRBaseTest,
                                         ApiCreateApprovalHandlerTestMixin):
  """Test for ApiCreateClientApprovalHandler."""

  APPROVAL_TYPE = aff4_security.ClientApproval

  def setUp(self):
    super(ApiCreateClientApprovalHandlerTest, self).setUp()

    self.SetUpApprovalTest()

    self.subject_urn = client_id = self.SetupClients(1)[0]

    self.handler = user_plugin.ApiCreateClientApprovalHandler()

    self.args = user_plugin.ApiCreateClientApprovalArgs(client_id=client_id)
    self.args.approval.reason = self.token.reason
    self.args.approval.notified_users = ["approver"]
    self.args.approval.email_cc_addresses = ["test@example.com"]

  def testKeepAliveFlowIsStartedWhenFlagIsSet(self):
    self.args.keep_client_alive = True

    self.handler.Handle(self.args, self.token)
    flows = aff4.FACTORY.Open(
        self.subject_urn.Add("flows"), token=self.token).OpenChildren()
    keep_alive_flow = [f for f in flows
                       if f.__class__ == administrative.KeepAlive]
    self.assertEqual(len(keep_alive_flow), 1)


class ApiCreateClientApprovalHandlerRegressionTest(
    api_test_lib.ApiCallHandlerRegressionTest):
  """Regression test for ApiCreateClientApprovalHandler."""

  handler = "ApiCreateClientApprovalHandler"

  def Run(self):
    with test_lib.FakeTime(42):
      self.CreateUser("approver")

      client_id = self.SetupClients(1)[0]

      # Delete the certificate as it's being regenerated every time the
      # client is created.
      with aff4.FACTORY.Open(
          client_id, mode="rw", token=self.token) as grr_client:
        grr_client.DeleteAttribute(grr_client.Schema.CERT)

    def ReplaceApprovalId():
      approvals = list(
          aff4.FACTORY.ListChildren(
              aff4.ROOT_URN.Add("ACL").Add(client_id.Basename()).Add(
                  self.token.username),
              token=self.token))

      return {approvals[0].Basename(): "approval:112233"}

    with test_lib.FakeTime(126):
      self.Check(
          "POST",
          "/api/users/me/approvals/client/%s" % client_id.Basename(),
          {"approval": {
              "reason": "really important reason!",
              "notified_users": ["approver1", "approver2"],
              "email_cc_addresses": ["test@example.com"]
          }},
          replace=ReplaceApprovalId)


class ApiListClientApprovalsHandlerTest(test_lib.GRRBaseTest):
  """Test for ApiListApprovalsHandler."""

  CLIENT_COUNT = 5

  def setUp(self):
    super(ApiListClientApprovalsHandlerTest, self).setUp()
    self.handler = user_plugin.ApiListClientApprovalsHandler()
    self.client_ids = self.SetupClients(self.CLIENT_COUNT)

  def _RequestClientApprovals(self):
    for client_id in self.client_ids:
      self.RequestClientApproval(client_id, token=self.token)

  def testRendersRequestedClientApprovals(self):
    self._RequestClientApprovals()

    args = user_plugin.ApiListClientApprovalsArgs()
    result = self.handler.Handle(args, token=self.token)

    # All approvals should be returned.
    self.assertEqual(len(result.items), self.CLIENT_COUNT)

  def testFiltersApprovalsByClientId(self):
    client_id = self.client_ids[0]

    self._RequestClientApprovals()

    # Get approvals for a specific client. There should be exactly one.
    args = user_plugin.ApiListClientApprovalsArgs(client_id=client_id)
    result = self.handler.Handle(args, token=self.token)

    self.assertEqual(len(result.items), 1)
    self.assertEqual(result.items[0].subject.urn, client_id)

  def testFiltersApprovalsByInvalidState(self):
    self._RequestClientApprovals()

    # We only requested approvals so far, so all of them should be invalid.
    args = user_plugin.ApiListClientApprovalsArgs(
        state=user_plugin.ApiListClientApprovalsArgs.State.INVALID)
    result = self.handler.Handle(args, token=self.token)

    self.assertEqual(len(result.items), self.CLIENT_COUNT)

    # Grant access to one client. Now all but one should be invalid.
    self.GrantClientApproval(
        self.client_ids[0], self.token.username, reason=self.token.reason)
    result = self.handler.Handle(args, token=self.token)
    self.assertEqual(len(result.items), self.CLIENT_COUNT - 1)

  def testFiltersApprovalsByValidState(self):
    self._RequestClientApprovals()

    # We only requested approvals so far, so none of them is valid.
    args = user_plugin.ApiListClientApprovalsArgs(
        state=user_plugin.ApiListClientApprovalsArgs.State.VALID)
    result = self.handler.Handle(args, token=self.token)

    # We do not have any approved approvals yet.
    self.assertEqual(len(result.items), 0)

    # Grant access to one client. Now exactly one approval should be valid.
    self.GrantClientApproval(
        self.client_ids[0], self.token.username, reason=self.token.reason)
    result = self.handler.Handle(args, token=self.token)
    self.assertEqual(len(result.items), 1)
    self.assertEqual(result.items[0].subject.urn, self.client_ids[0])

  def testFiltersApprovalsByClientIdAndState(self):
    client_id = self.client_ids[0]

    self._RequestClientApprovals()

    # Grant approval to a certain client.
    self.GrantClientApproval(
        client_id, self.token.username, reason=self.token.reason)

    args = user_plugin.ApiListClientApprovalsArgs(
        client_id=client_id,
        state=user_plugin.ApiListClientApprovalsArgs.State.VALID)
    result = self.handler.Handle(args, token=self.token)

    # We have a valid approval for the requested client.
    self.assertEqual(len(result.items), 1)

    args.state = user_plugin.ApiListClientApprovalsArgs.State.INVALID
    result = self.handler.Handle(args, token=self.token)

    # However, we do not have any invalid approvals for the client.
    self.assertEqual(len(result.items), 0)

  def testFilterConsidersOffsetAndCount(self):
    client_id = self.client_ids[0]

    # Create five approval requests without granting them.
    for i in range(10):
      with test_lib.FakeTime(42 + i):
        self.token.reason = "Request reason %d" % i
        self.RequestClientApproval(client_id, token=self.token)

    args = user_plugin.ApiListClientApprovalsArgs(
        client_id=client_id, offset=0, count=5)
    result = self.handler.Handle(args, token=self.token)

    # Approvals are returned newest to oldest, so the first five approvals
    # have reason 9 to 5.
    self.assertEqual(len(result.items), 5)
    for item, i in zip(result.items, reversed(range(6, 10))):
      self.assertEqual(item.reason, "Request reason %d" % i)

    # When no count is specified, take all items from offset to the end.
    args = user_plugin.ApiListClientApprovalsArgs(client_id=client_id, offset=7)
    result = self.handler.Handle(args, token=self.token)

    self.assertEqual(len(result.items), 4)
    for item, i in zip(result.items, reversed(range(0, 4))):
      self.assertEqual(item.reason, "Request reason %d" % i)


class ApiListClientApprovalsHandlerRegressionTest(
    api_test_lib.ApiCallHandlerRegressionTest):
  """Regression test for ApiListClientApprovalsHandlerTest."""

  handler = "ApiListClientApprovalsHandler"

  def Run(self):
    with test_lib.FakeTime(42):
      self.CreateAdminUser("approver")

      clients = self.SetupClients(2)
      for client_id in clients:
        # Delete the certificate as it's being regenerated every time the
        # client is created.
        with aff4.FACTORY.Open(
            client_id, mode="rw", token=self.token) as grr_client:
          grr_client.DeleteAttribute(grr_client.Schema.CERT)

    with test_lib.FakeTime(44):
      flow_urn = flow.GRRFlow.StartFlow(
          client_id=clients[0],
          flow_name="RequestClientApprovalFlow",
          reason=self.token.reason,
          subject_urn=clients[0],
          approver="approver",
          token=self.token)
      flow_fd = aff4.FACTORY.Open(
          flow_urn, aff4_type=flow.GRRFlow, token=self.token)
      approval1_id = flow_fd.state.approval_id

    with test_lib.FakeTime(45):
      flow_urn = flow.GRRFlow.StartFlow(
          client_id=clients[1],
          flow_name="RequestClientApprovalFlow",
          reason=self.token.reason,
          subject_urn=clients[1],
          approver="approver",
          token=self.token)
      flow_fd = aff4.FACTORY.Open(
          flow_urn, aff4_type=flow.GRRFlow, token=self.token)
      approval2_id = flow_fd.state.approval_id

    with test_lib.FakeTime(84):
      approver_token = access_control.ACLToken(username="approver")
      flow.GRRFlow.StartFlow(
          client_id=clients[1],
          flow_name="GrantClientApprovalFlow",
          reason=self.token.reason,
          delegate=self.token.username,
          subject_urn=clients[1],
          token=approver_token)

    with test_lib.FakeTime(126):
      self.Check(
          "GET",
          "/api/users/me/approvals/client",
          replace={approval1_id: "approval:111111",
                   approval2_id: "approval:222222"})
      self.Check(
          "GET",
          "/api/users/me/approvals/client/%s" % (clients[0].Basename()),
          replace={approval1_id: "approval:111111",
                   approval2_id: "approval:222222"})


class ApiGetHuntApprovalHandlerRegressionTest(
    api_test_lib.ApiCallHandlerRegressionTest,
    standard_test.StandardHuntTestMixin):
  """Regression test for ApiGetHuntApprovalHandler."""

  handler = "ApiGetHuntApprovalHandler"

  def Run(self):
    with test_lib.FakeTime(42):
      self.CreateAdminUser("approver")

      with self.CreateHunt(description="hunt1") as hunt_obj:
        hunt1_urn = hunt_obj.urn
        hunt1_id = hunt1_urn.Basename()

      with self.CreateHunt(description="hunt2") as hunt_obj:
        hunt2_urn = hunt_obj.urn
        hunt2_id = hunt2_urn.Basename()

    with test_lib.FakeTime(44):
      flow_urn = flow.GRRFlow.StartFlow(
          flow_name="RequestHuntApprovalFlow",
          reason="foo",
          subject_urn=hunt1_urn,
          approver="approver",
          token=self.token)
      flow_fd = aff4.FACTORY.Open(
          flow_urn, aff4_type=flow.GRRFlow, token=self.token)
      approval1_id = flow_fd.state.approval_id

    with test_lib.FakeTime(45):
      flow_urn = flow.GRRFlow.StartFlow(
          flow_name="RequestHuntApprovalFlow",
          reason="bar",
          subject_urn=hunt2_urn,
          approver="approver",
          token=self.token)
      flow_fd = aff4.FACTORY.Open(
          flow_urn, aff4_type=flow.GRRFlow, token=self.token)
      approval2_id = flow_fd.state.approval_id

    with test_lib.FakeTime(84):
      approver_token = access_control.ACLToken(username="approver")
      flow.GRRFlow.StartFlow(
          flow_name="GrantHuntApprovalFlow",
          reason="bar",
          delegate=self.token.username,
          subject_urn=hunt2_urn,
          token=approver_token)

    with test_lib.FakeTime(126):
      self.Check(
          "GET",
          "/api/users/test/approvals/hunt/%s/%s" % (hunt1_id, approval1_id),
          replace={hunt1_id: "H:123456",
                   approval1_id: "approval:111111"})
      self.Check(
          "GET",
          "/api/users/test/approvals/hunt/%s/%s" % (hunt2_id, approval2_id),
          replace={hunt2_id: "H:567890",
                   approval2_id: "approval:222222"})


class ApiGrantHuntApprovalHandlerRegressionTest(
    api_test_lib.ApiCallHandlerRegressionTest,
    standard_test.StandardHuntTestMixin):
  """Regression test for ApiGrantHuntApprovalHandler."""

  handler = "ApiGrantHuntApprovalHandler"

  def Run(self):
    with test_lib.FakeTime(42):
      self.CreateAdminUser("requestor")

      with self.CreateHunt(description="a hunt") as hunt_obj:
        hunt_urn = hunt_obj.urn
        hunt_id = hunt_urn.Basename()

    with test_lib.FakeTime(44):
      requestor_token = access_control.ACLToken(username="requestor")
      flow_urn = flow.GRRFlow.StartFlow(
          flow_name="RequestHuntApprovalFlow",
          reason="foo",
          subject_urn=hunt_urn,
          approver=self.token.username,
          token=requestor_token)
      flow_fd = aff4.FACTORY.Open(
          flow_urn, aff4_type=flow.GRRFlow, token=self.token)
      approval_id = flow_fd.state.approval_id

    with test_lib.FakeTime(126):
      self.Check(
          "POST",
          "/api/users/requestor/approvals/hunt/%s/%s/actions/grant" %
          (hunt_id, approval_id),
          replace={hunt_id: "H:123456",
                   approval_id: "approval:111111"})


class ApiCreateHuntApprovalHandlerTest(test_lib.GRRBaseTest,
                                       ApiCreateApprovalHandlerTestMixin,
                                       standard_test.StandardHuntTestMixin):
  """Test for ApiCreateHuntApprovalHandler."""

  APPROVAL_TYPE = aff4_security.HuntApproval

  def setUp(self):
    super(ApiCreateHuntApprovalHandlerTest, self).setUp()

    self.SetUpApprovalTest()

    with self.CreateHunt(description="foo") as hunt_obj:
      self.subject_urn = hunt_urn = hunt_obj.urn
      hunt_id = hunt_urn.Basename()

    self.handler = user_plugin.ApiCreateHuntApprovalHandler()

    self.args = user_plugin.ApiCreateHuntApprovalArgs(hunt_id=hunt_id)
    self.args.approval.reason = self.token.reason
    self.args.approval.notified_users = ["approver"]
    self.args.approval.email_cc_addresses = ["test@example.com"]


class ApiCreateHuntApprovalHandlerRegressionTest(
    api_test_lib.ApiCallHandlerRegressionTest,
    standard_test.StandardHuntTestMixin):
  """Regression test for ApiCreateHuntApprovalHandler."""

  handler = "ApiCreateHuntApprovalHandler"

  def Run(self):
    with test_lib.FakeTime(42):
      self.CreateUser("approver")

      with self.CreateHunt(description="foo") as hunt_obj:
        hunt_id = hunt_obj.urn.Basename()

    def ReplaceHuntAndApprovalIds():
      approvals = list(
          aff4.FACTORY.ListChildren(
              aff4.ROOT_URN.Add("ACL").Add("hunts").Add(hunt_id).Add(
                  self.token.username),
              token=self.token))

      return {approvals[0].Basename(): "approval:112233", hunt_id: "H:123456"}

    with test_lib.FakeTime(126):
      self.Check(
          "POST",
          "/api/users/me/approvals/hunt/%s" % hunt_id, {"approval": {
              "reason": "really important reason!",
              "notified_users": ["approver1", "approver2"],
              "email_cc_addresses": ["test@example.com"]
          }},
          replace=ReplaceHuntAndApprovalIds)


class ApiListHuntApprovalsHandlerTest(test_lib.GRRBaseTest):
  """Test for ApiListHuntApprovalsHandler."""

  def setUp(self):
    super(ApiListHuntApprovalsHandlerTest, self).setUp()
    self.handler = user_plugin.ApiListHuntApprovalsHandler()

  def testRendersRequestedHuntAppoval(self):
    with hunts.GRRHunt.StartHunt(
        hunt_name=standard.SampleHunt.__name__, token=self.token) as hunt:
      pass

    flow.GRRFlow.StartFlow(
        flow_name="RequestHuntApprovalFlow",
        reason=self.token.reason,
        subject_urn=hunt.urn,
        approver="approver",
        token=self.token)

    args = user_plugin.ApiListHuntApprovalsArgs()
    result = self.handler.Handle(args, token=self.token)

    self.assertEqual(len(result.items), 1)


class ApiListHuntApprovalsHandlerRegressionTest(
    api_test_lib.ApiCallHandlerRegressionTest):
  """Regression test for ApiListClientApprovalsHandlerTest."""

  handler = "ApiListHuntApprovalsHandler"

  def Run(self):
    with test_lib.FakeTime(42):
      self.CreateAdminUser("approver")

      hunt = hunts.GRRHunt.StartHunt(hunt_name="GenericHunt", token=self.token)

    with test_lib.FakeTime(43):
      flow_urn = flow.GRRFlow.StartFlow(
          flow_name="RequestHuntApprovalFlow",
          reason=self.token.reason,
          subject_urn=hunt.urn,
          approver="approver",
          token=self.token)
      flow_fd = aff4.FACTORY.Open(
          flow_urn, aff4_type=flow.GRRFlow, token=self.token)
      approval_id = flow_fd.state.approval_id

    with test_lib.FakeTime(126):
      self.Check(
          "GET",
          "/api/users/me/approvals/hunt",
          replace={hunt.urn.Basename(): "H:123456",
                   approval_id: "approval:112233"})


class ApiGetCronJobApprovalHandlerRegressionTest(
    api_test_lib.ApiCallHandlerRegressionTest):
  """Regression test for ApiGetCronJobApprovalHandler."""

  handler = "ApiGetCronJobApprovalHandler"

  def Run(self):
    with test_lib.FakeTime(42):
      self.CreateAdminUser("approver")

      cron_manager = aff4_cronjobs.CronManager()
      cron_args = aff4_cronjobs.CreateCronJobFlowArgs(
          periodicity="1d", allow_overruns=False)
      cron1_urn = cron_manager.ScheduleFlow(
          cron_args=cron_args, token=self.token)
      cron2_urn = cron_manager.ScheduleFlow(
          cron_args=cron_args, token=self.token)

    with test_lib.FakeTime(44):
      flow_urn = flow.GRRFlow.StartFlow(
          flow_name="RequestCronJobApprovalFlow",
          reason="foo",
          subject_urn=cron1_urn,
          approver="approver",
          token=self.token)
      flow_fd = aff4.FACTORY.Open(
          flow_urn, aff4_type=flow.GRRFlow, token=self.token)
      approval1_id = flow_fd.state.approval_id

    with test_lib.FakeTime(45):
      flow_urn = flow.GRRFlow.StartFlow(
          flow_name="RequestCronJobApprovalFlow",
          reason="bar",
          subject_urn=cron2_urn,
          approver="approver",
          token=self.token)
      flow_fd = aff4.FACTORY.Open(
          flow_urn, aff4_type=flow.GRRFlow, token=self.token)
      approval2_id = flow_fd.state.approval_id

    with test_lib.FakeTime(84):
      approver_token = access_control.ACLToken(username="approver")
      flow.GRRFlow.StartFlow(
          flow_name="GrantCronJobApprovalFlow",
          reason="bar",
          delegate=self.token.username,
          subject_urn=cron2_urn,
          token=approver_token)

    with test_lib.FakeTime(126):
      self.Check(
          "GET",
          "/api/users/test/approvals/cron-job/%s/%s" %
          (cron1_urn.Basename(), approval1_id),
          replace={cron1_urn.Basename(): "CronJob_123456",
                   approval1_id: "approval:111111"})
      self.Check(
          "GET",
          "/api/users/test/approvals/cron-job/%s/%s" %
          (cron2_urn.Basename(), approval2_id),
          replace={cron2_urn.Basename(): "CronJob_567890",
                   approval2_id: "approval:222222"})


class ApiGrantCronJobApprovalHandlerRegressionTest(
    api_test_lib.ApiCallHandlerRegressionTest):
  """Regression test for ApiGrantCronJobApprovalHandler."""

  handler = "ApiGrantCronJobApprovalHandler"

  def Run(self):
    with test_lib.FakeTime(42):
      self.CreateAdminUser("requestor")

      cron_manager = aff4_cronjobs.CronManager()
      cron_args = aff4_cronjobs.CreateCronJobFlowArgs(
          periodicity="1d", allow_overruns=False)
      cron_urn = cron_manager.ScheduleFlow(
          cron_args=cron_args, token=self.token)

    with test_lib.FakeTime(44):
      requestor_token = access_control.ACLToken(username="requestor")
      flow_urn = flow.GRRFlow.StartFlow(
          flow_name="RequestCronJobApprovalFlow",
          reason="foo",
          subject_urn=cron_urn,
          approver=self.token.username,
          token=requestor_token)
      flow_fd = aff4.FACTORY.Open(
          flow_urn, aff4_type=flow.GRRFlow, token=self.token)
      approval_id = flow_fd.state.approval_id

    with test_lib.FakeTime(126):
      self.Check(
          "POST",
          "/api/users/requestor/approvals/cron-job/%s/%s/actions/grant" %
          (cron_urn.Basename(), approval_id),
          replace={cron_urn.Basename(): "CronJob_123456",
                   approval_id: "approval:111111"})


class ApiCreateCronJobApprovalHandlerTest(test_lib.GRRBaseTest,
                                          ApiCreateApprovalHandlerTestMixin):
  """Test for ApiCreateCronJobApprovalHandler."""

  APPROVAL_TYPE = aff4_security.CronJobApproval

  def setUp(self):
    super(ApiCreateCronJobApprovalHandlerTest, self).setUp()

    self.SetUpApprovalTest()

    cron_manager = aff4_cronjobs.CronManager()
    cron_args = aff4_cronjobs.CreateCronJobFlowArgs(
        periodicity="1d", allow_overruns=False)
    self.subject_urn = cron_urn = cron_manager.ScheduleFlow(
        cron_args=cron_args, token=self.token)
    cron_id = cron_urn.Basename()

    self.handler = user_plugin.ApiCreateCronJobApprovalHandler()

    self.args = user_plugin.ApiCreateCronJobApprovalArgs(cron_job_id=cron_id)
    self.args.approval.reason = self.token.reason
    self.args.approval.notified_users = ["approver"]
    self.args.approval.email_cc_addresses = ["test@example.com"]


class ApiCreateCronJobApprovalHandlerRegressionTest(
    api_test_lib.ApiCallHandlerRegressionTest):
  """Regression test for ApiCreateCronJobApprovalHandler."""

  handler = "ApiCreateCronJobApprovalHandler"

  def Run(self):
    with test_lib.FakeTime(42):
      self.CreateUser("approver")

    cron_manager = aff4_cronjobs.CronManager()
    cron_args = aff4_cronjobs.CreateCronJobFlowArgs(
        periodicity="1d", allow_overruns=False)
    cron_urn = cron_manager.ScheduleFlow(cron_args=cron_args, token=self.token)
    cron_id = cron_urn.Basename()

    def ReplaceCronAndApprovalIds():
      approvals = list(
          aff4.FACTORY.ListChildren(
              aff4.ROOT_URN.Add("ACL").Add("cron").Add(cron_id).Add(
                  self.token.username),
              token=self.token))

      return {approvals[0].Basename(): "approval:112233",
              cron_id: "CronJob_123456"}

    with test_lib.FakeTime(126):
      self.Check(
          "POST",
          "/api/users/me/approvals/cron-job/%s" % cron_id, {"approval": {
              "reason": "really important reason!",
              "notified_users": ["approver1", "approver2"],
              "email_cc_addresses": ["test@example.com"]
          }},
          replace=ReplaceCronAndApprovalIds)


class ApiListCronJobApprovalsHandlerTest(test_lib.GRRBaseTest):
  """Test for ApiListCronJobApprovalsHandler."""

  def setUp(self):
    super(ApiListCronJobApprovalsHandlerTest, self).setUp()
    self.handler = user_plugin.ApiListCronJobApprovalsHandler()

  def testRendersRequestedCronJobApproval(self):
    cron_manager = aff4_cronjobs.CronManager()
    cron_args = aff4_cronjobs.CreateCronJobFlowArgs(
        periodicity="1d", allow_overruns=False)
    cron_job_urn = cron_manager.ScheduleFlow(
        cron_args=cron_args, token=self.token)

    flow.GRRFlow.StartFlow(
        flow_name="RequestCronJobApprovalFlow",
        reason=self.token.reason,
        subject_urn=cron_job_urn,
        approver="approver",
        token=self.token)

    args = user_plugin.ApiListCronJobApprovalsArgs()
    result = self.handler.Handle(args, token=self.token)

    self.assertEqual(len(result.items), 1)


class ApiGetGrrUserHandlerTest(test_lib.GRRBaseTest):
  """Test for ApiGetUserSettingsHandler."""

  def setUp(self):
    super(ApiGetGrrUserHandlerTest, self).setUp()
    self.handler = user_plugin.ApiGetGrrUserHandler()

  def testRendersObjectForNonExistingUser(self):
    result = self.handler.Handle(
        None, token=access_control.ACLToken(username="foo"))
    self.assertEqual(result.username, "foo")

  def testRendersSettingsForUserCorrespondingToToken(self):
    with aff4.FACTORY.Create(
        aff4.ROOT_URN.Add("users").Add("foo"),
        aff4_type=aff4_users.GRRUser,
        mode="w",
        token=self.token) as user_fd:
      user_fd.Set(user_fd.Schema.GUI_SETTINGS,
                  aff4_users.GUISettings(
                      mode="ADVANCED", canary_mode=True,
                      docs_location="REMOTE"))

    result = self.handler.Handle(
        None, token=access_control.ACLToken(username="foo"))
    self.assertEqual(result.settings.mode, "ADVANCED")
    self.assertEqual(result.settings.canary_mode, True)
    self.assertEqual(result.settings.docs_location, "REMOTE")

  def testRendersTraitsPassedInConstructor(self):
    result = self.handler.Handle(
        None, token=access_control.ACLToken(username="foo"))
    self.assertFalse(result.interface_traits.create_hunt_action_enabled)

    handler = user_plugin.ApiGetGrrUserHandler(
        interface_traits=user_plugin.ApiGrrUserInterfaceTraits(
            create_hunt_action_enabled=True))
    result = handler.Handle(None, token=access_control.ACLToken(username="foo"))
    self.assertTrue(result.interface_traits.create_hunt_action_enabled)


class ApiGetGrrUserHandlerRegresstionTest(
    api_test_lib.ApiCallHandlerRegressionTest):
  """Regression test for ApiGetUserSettingsHandler."""

  handler = "ApiGetGrrUserHandler"

  def Run(self):
    with test_lib.FakeTime(42):
      with aff4.FACTORY.Create(
          aff4.ROOT_URN.Add("users").Add(self.token.username),
          aff4_type=aff4_users.GRRUser,
          mode="w",
          token=self.token) as user_fd:
        user_fd.Set(user_fd.Schema.GUI_SETTINGS,
                    aff4_users.GUISettings(canary_mode=True))

    self.Check("GET", "/api/users/me")


class ApiUpdateGrrUserHandlerTest(test_lib.GRRBaseTest):
  """Tests for ApiUpdateUserSettingsHandler."""

  def setUp(self):
    super(ApiUpdateGrrUserHandlerTest, self).setUp()
    self.handler = user_plugin.ApiUpdateGrrUserHandler()

  def testRaisesIfUsernameSetInRequest(self):
    user = user_plugin.ApiGrrUser(username="foo")
    with self.assertRaises(ValueError):
      self.handler.Handle(user, token=access_control.ACLToken(username="foo"))

    user = user_plugin.ApiGrrUser(username="bar")
    with self.assertRaises(ValueError):
      self.handler.Handle(user, token=access_control.ACLToken(username="foo"))

  def testRaisesIfTraitsSetInRequest(self):
    user = user_plugin.ApiGrrUser(
        interface_traits=user_plugin.ApiGrrUserInterfaceTraits())
    with self.assertRaises(ValueError):
      self.handler.Handle(user, token=access_control.ACLToken(username="foo"))

  def testSetsSettingsForUserCorrespondingToToken(self):
    settings = aff4_users.GUISettings(
        mode="ADVANCED", canary_mode=True, docs_location="REMOTE")
    user = user_plugin.ApiGrrUser(settings=settings)

    self.handler.Handle(user, token=access_control.ACLToken(username="foo"))

    # Check that settings for user "foo" were applied.
    fd = aff4.FACTORY.Open("aff4:/users/foo", token=self.token)
    self.assertEqual(fd.Get(fd.Schema.GUI_SETTINGS), settings)


class ApiGetPendingUserNotificationsCountHandlerRegressionTest(
    api_test_lib.ApiCallHandlerRegressionTest):
  """Regression test for ApiGetPendingUserNotificationsCountHandler."""

  handler = "ApiGetPendingUserNotificationsCountHandler"

  def setUp(self):
    super(ApiGetPendingUserNotificationsCountHandlerRegressionTest,
          self).setUp()
    self.client_id = self.SetupClients(1)[0]

  def Run(self):
    self._SendNotification(
        notification_type="Discovery",
        subject="<some client urn>",
        message="<some message>",
        client_id=self.client_id)
    self._SendNotification(
        notification_type="ViewObject",
        subject=str(self.client_id),
        message="<some other message>",
        client_id=self.client_id)

    self.Check("GET", "/api/users/me/notifications/pending/count")


class ApiListPendingUserNotificationsHandlerRegressionTest(
    api_test_lib.ApiCallHandlerRegressionTest):
  """Regression test for ApiListPendingUserNotificationsHandler."""

  handler = "ApiListPendingUserNotificationsHandler"

  def setUp(self):
    super(ApiListPendingUserNotificationsHandlerRegressionTest, self).setUp()
    self.client_id = self.SetupClients(1)[0]

  def Run(self):
    with test_lib.FakeTime(42):
      self._SendNotification(
          notification_type="Discovery",
          subject=str(self.client_id),
          message="<some message>",
          client_id=self.client_id)

    with test_lib.FakeTime(44):
      self._SendNotification(
          notification_type="ViewObject",
          subject=str(self.client_id),
          message="<some other message>",
          client_id=self.client_id)

    base_url = "/api/users/me/notifications/pending"
    self.Check("GET", base_url)
    self.Check("GET", base_url + "?timestamp=43000000")


class ApiDeletePendingUserNotificationHandlerTest(test_lib.GRRBaseTest):
  """Test for ApiDeletePendingUserNotificationHandler."""

  TIME_0 = rdfvalue.RDFDatetime(42 * rdfvalue.MICROSECONDS)
  TIME_1 = TIME_0 + rdfvalue.Duration("1d")
  TIME_2 = TIME_1 + rdfvalue.Duration("1d")

  def setUp(self):
    super(ApiDeletePendingUserNotificationHandlerTest, self).setUp()
    self.handler = user_plugin.ApiDeletePendingUserNotificationHandler()
    self.client_id = self.SetupClients(1)[0]

    with test_lib.FakeTime(self.TIME_0):
      self._SendNotification(
          notification_type="Discovery",
          subject=str(self.client_id),
          message="<some message>",
          client_id=self.client_id)

      self._SendNotification(
          notification_type="Discovery",
          subject=str(self.client_id),
          message="<some message with identical time>",
          client_id=self.client_id)

    with test_lib.FakeTime(self.TIME_1):
      self._SendNotification(
          notification_type="ViewObject",
          subject=str(self.client_id),
          message="<some other message>",
          client_id=self.client_id)

  def _GetNotifications(self):
    user_record = aff4.FACTORY.Create(
        aff4.ROOT_URN.Add("users").Add(self.token.username),
        aff4_type=aff4_users.GRRUser,
        mode="r",
        token=self.token)

    pending = user_record.Get(user_record.Schema.PENDING_NOTIFICATIONS)
    shown = user_record.Get(user_record.Schema.SHOWN_NOTIFICATIONS)
    return (pending, shown)

  def testDeletesFromPendingAndAddsToShown(self):
    # Check that there are three pending notifications and no shown ones yet.
    (pending, shown) = self._GetNotifications()
    self.assertEqual(len(pending), 3)
    self.assertEqual(len(shown), 0)

    # Delete a pending notification.
    args = user_plugin.ApiDeletePendingUserNotificationArgs(
        timestamp=self.TIME_1)
    self.handler.Handle(args, token=self.token)

    # After the deletion, two notifications should be pending and one shown.
    (pending, shown) = self._GetNotifications()
    self.assertEqual(len(pending), 2)
    self.assertEqual(len(shown), 1)
    self.assertTrue("<some other message>" in shown[0].message)
    self.assertEqual(shown[0].timestamp, self.TIME_1)

  def testRaisesOnDeletingMultipleNotifications(self):
    # Check that there are three pending notifications and no shown ones yet.
    (pending, shown) = self._GetNotifications()
    self.assertEqual(len(pending), 3)
    self.assertEqual(len(shown), 0)

    # Delete all pending notifications on TIME_0.
    args = user_plugin.ApiDeletePendingUserNotificationArgs(
        timestamp=self.TIME_0)
    with self.assertRaises(aff4_users.UniqueKeyError):
      self.handler.Handle(args, token=self.token)

    # Check that the notifications were not changed in the process.
    (pending, shown) = self._GetNotifications()
    self.assertEqual(len(pending), 3)
    self.assertEqual(len(shown), 0)

  def testUnknownTimestampIsIgnored(self):
    # Check that there are three pending notifications and no shown ones yet.
    (pending, shown) = self._GetNotifications()
    self.assertEqual(len(pending), 3)
    self.assertEqual(len(shown), 0)

    # A timestamp not matching any pending notifications does not change any of
    # the collections.
    args = user_plugin.ApiDeletePendingUserNotificationArgs(
        timestamp=self.TIME_2)
    self.handler.Handle(args, token=self.token)

    # We should still have the same number of pending and shown notifications.
    (pending, shown) = self._GetNotifications()
    self.assertEqual(len(pending), 3)
    self.assertEqual(len(shown), 0)


class ApiListAndResetUserNotificationsHandlerRegressionTest(
    api_test_lib.ApiCallHandlerRegressionTest):
  """Regression test for ApiListAndResetUserNotificationsHandler."""

  handler = "ApiListAndResetUserNotificationsHandler"

  def setUp(self):
    super(ApiListAndResetUserNotificationsHandlerRegressionTest, self).setUp()
    self.client_id = self.SetupClients(1)[0]

  def Run(self):
    with test_lib.FakeTime(42):
      self._SendNotification(
          notification_type="Discovery",
          subject=str(self.client_id),
          message="<some message>",
          client_id=self.client_id)

    with test_lib.FakeTime(44):
      self._SendNotification(
          notification_type="ViewObject",
          subject=str(self.client_id),
          message="<some other message>",
          client_id=self.client_id)

    # Notifications are pending in this request.
    self.Check("POST", "/api/users/me/notifications")

    # But not anymore in these requests.
    self.Check("POST", "/api/users/me/notifications?offset=1&count=1")
    self.Check("POST", "/api/users/me/notifications?filter=other")


class ApiListPendingGlobalNotificationsHandlerRegressionTest(
    api_test_lib.ApiCallHandlerRegressionTest):
  """Regression test for ApiListPendingGlobalNotificationsHandler."""

  handler = "ApiListPendingGlobalNotificationsHandler"

  # Global notifications are only shown in a certain time interval. By default,
  # this is from the moment they are created until two weeks later. Create
  # a notification that is too old to be returned and two valid ones.
  NOW = rdfvalue.RDFDatetime.Now()
  TIME_TOO_EARLY = NOW - rdfvalue.Duration("4w")
  TIME_0 = NOW - rdfvalue.Duration("12h")
  TIME_1 = NOW - rdfvalue.Duration("1h")

  def setUp(self):
    super(ApiListPendingGlobalNotificationsHandlerRegressionTest, self).setUp()

  def Run(self):
    with aff4.FACTORY.Create(
        aff4_users.GlobalNotificationStorage.DEFAULT_PATH,
        aff4_type=aff4_users.GlobalNotificationStorage,
        mode="rw",
        token=self.token) as storage:
      storage.AddNotification(
          aff4_users.GlobalNotification(
              type=aff4_users.GlobalNotification.Type.ERROR,
              header="Oh no, we're doomed!",
              content="Houston, Houston, we have a prob...",
              link="http://www.google.com",
              show_from=self.TIME_0))

      storage.AddNotification(
          aff4_users.GlobalNotification(
              type=aff4_users.GlobalNotification.Type.INFO,
              header="Nothing to worry about!",
              link="http://www.google.com",
              show_from=self.TIME_1))

      storage.AddNotification(
          aff4_users.GlobalNotification(
              type=aff4_users.GlobalNotification.Type.WARNING,
              header="Nothing to worry, we won't see this!",
              link="http://www.google.com",
              show_from=self.TIME_TOO_EARLY))

    replace = {("%d" % self.TIME_0.AsMicroSecondsFromEpoch()): "0",
               ("%d" % self.TIME_1.AsMicroSecondsFromEpoch()): "0"}

    self.Check(
        "GET", "/api/users/me/notifications/pending/global", replace=replace)


class ApiDeletePendingGlobalNotificationHandlerTest(test_lib.GRRBaseTest):
  """Test for ApiDeletePendingGlobalNotificationHandler."""

  def setUp(self):
    super(ApiDeletePendingGlobalNotificationHandlerTest, self).setUp()
    self.handler = user_plugin.ApiDeletePendingGlobalNotificationHandler()

    with aff4.FACTORY.Create(
        aff4_users.GlobalNotificationStorage.DEFAULT_PATH,
        aff4_type=aff4_users.GlobalNotificationStorage,
        mode="rw",
        token=self.token) as storage:
      storage.AddNotification(
          aff4_users.GlobalNotification(
              type=aff4_users.GlobalNotification.Type.ERROR,
              header="Oh no, we're doomed!",
              content="Houston, Houston, we have a prob...",
              link="http://www.google.com"))
      storage.AddNotification(
          aff4_users.GlobalNotification(
              type=aff4_users.GlobalNotification.Type.INFO,
              header="Nothing to worry about!",
              link="http://www.google.com"))

  def _GetGlobalNotifications(self):
    user_record = aff4.FACTORY.Create(
        aff4.ROOT_URN.Add("users").Add(self.token.username),
        aff4_type=aff4_users.GRRUser,
        mode="r",
        token=self.token)

    pending = user_record.GetPendingGlobalNotifications()
    shown = list(user_record.Get(user_record.Schema.SHOWN_GLOBAL_NOTIFICATIONS))
    return (pending, shown)

  def testDeletesFromPendingAndAddsToShown(self):
    # Check that there are two pending notifications and no shown ones yet.
    (pending, shown) = self._GetGlobalNotifications()
    self.assertEqual(len(pending), 2)
    self.assertEqual(len(shown), 0)

    # Delete one of the pending notifications.
    args = user_plugin.ApiDeletePendingGlobalNotificationArgs(
        type=aff4_users.GlobalNotification.Type.INFO)
    self.handler.Handle(args, token=self.token)

    # After the deletion, one notification should be pending and one shown.
    (pending, shown) = self._GetGlobalNotifications()
    self.assertEqual(len(pending), 1)
    self.assertEqual(len(shown), 1)
    self.assertEqual(pending[0].header, "Oh no, we're doomed!")
    self.assertEqual(shown[0].header, "Nothing to worry about!")

  def testRaisesOnDeletingNonExistingNotification(self):
    # Check that there are two pending notifications and no shown ones yet.
    (pending, shown) = self._GetGlobalNotifications()
    self.assertEqual(len(pending), 2)
    self.assertEqual(len(shown), 0)

    # Delete a non-existing pending notification.
    args = user_plugin.ApiDeletePendingGlobalNotificationArgs(
        type=aff4_users.GlobalNotification.Type.WARNING)
    with self.assertRaises(user_plugin.GlobalNotificationNotFoundError):
      self.handler.Handle(args, token=self.token)

    # Check that the notifications were not changed in the process.
    (pending, shown) = self._GetGlobalNotifications()
    self.assertEqual(len(pending), 2)
    self.assertEqual(len(shown), 0)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
