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
from grr.lib import test_lib
from grr.lib import utils

from grr.lib.aff4_objects import security as aff4_security
from grr.lib.aff4_objects import users as aff4_users


class ApiGetUserClientApprovalHandlerTest(test_lib.GRRBaseTest):
  """Test for ApiGetUserClientApprovalHandler."""

  def setUp(self):
    super(ApiGetUserClientApprovalHandlerTest, self).setUp()
    self.client_id = self.SetupClients(1)[0]
    self.handler = user_plugin.ApiGetUserClientApprovalHandler()

  def testRendersRequestedClientApproval(self):
    flow.GRRFlow.StartFlow(client_id=self.client_id,
                           flow_name="RequestClientApprovalFlow",
                           reason="blah",
                           subject_urn=self.client_id,
                           approver="approver",
                           email_cc_address="test@example.com",
                           token=self.token)
    args = user_plugin.ApiGetUserClientApprovalArgs(
        client_id=self.client_id,
        reason="blah")
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
    flow.GRRFlow.StartFlow(client_id=self.client_id,
                           flow_name="RequestClientApprovalFlow",
                           reason="blah",
                           subject_urn=self.client_id,
                           approver="approver",
                           token=self.token)

    approver_token = access_control.ACLToken(username="approver")
    flow.GRRFlow.StartFlow(client_id=self.client_id,
                           flow_name="GrantClientApprovalFlow",
                           reason="blah",
                           delegate=self.token.username,
                           subject_urn=self.client_id,
                           token=approver_token)

    args = user_plugin.ApiGetUserClientApprovalArgs(
        client_id=self.client_id,
        reason="blah")
    result = self.handler.Handle(args, token=self.token)

    self.assertTrue(result.is_valid)
    self.assertEqual(sorted(result.approvers),
                     sorted([approver_token.username, self.token.username]))

  def testRaisesWhenApprovalIsNotFound(self):
    args = user_plugin.ApiGetUserClientApprovalArgs(
        client_id=self.client_id,
        reason="blah")

    # TODO(user): throw some standard exception that can be converted to
    # HTTP 404 status code.
    with self.assertRaises(IOError):
      self.handler.Handle(args, token=self.token)


class ApiGetUserClientApprovalHandlerRegressionTest(
    api_test_lib.ApiCallHandlerRegressionTest):
  """Regression test for ApiGetUserClientApprovalHandler."""

  handler = "ApiGetUserClientApprovalHandler"

  def Run(self):
    with test_lib.FakeTime(42):
      self.CreateAdminUser("approver")

      clients = self.SetupClients(2)
      for client_id in clients:
        # Delete the certificate as it's being regenerated every time the
        # client is created.
        with aff4.FACTORY.Open(client_id, mode="rw",
                               token=self.token) as grr_client:
          grr_client.DeleteAttribute(grr_client.Schema.CERT)

    with test_lib.FakeTime(44):
      flow.GRRFlow.StartFlow(client_id=clients[0],
                             flow_name="RequestClientApprovalFlow",
                             reason="foo",
                             subject_urn=clients[0],
                             approver="approver",
                             token=self.token)

    with test_lib.FakeTime(45):
      flow.GRRFlow.StartFlow(client_id=clients[1],
                             flow_name="RequestClientApprovalFlow",
                             reason="bar",
                             subject_urn=clients[1],
                             approver="approver",
                             token=self.token)

    with test_lib.FakeTime(84):
      approver_token = access_control.ACLToken(username="approver")
      flow.GRRFlow.StartFlow(client_id=clients[1],
                             flow_name="GrantClientApprovalFlow",
                             reason="bar",
                             delegate=self.token.username,
                             subject_urn=clients[1],
                             token=approver_token)

    with test_lib.FakeTime(126):
      self.Check("GET", "/api/users/me/approvals/client/%s/foo" %
                 clients[0].Basename())
      self.Check("GET", "/api/users/me/approvals/client/%s/bar" %
                 clients[1].Basename())


class ApiCreateUserClientApprovalHandlerTest(test_lib.GRRBaseTest):
  """Test for ApiCreateUserClientApprovalHandler."""

  def setUp(self):
    super(ApiCreateUserClientApprovalHandlerTest, self).setUp()
    self.client_id = self.SetupClients(1)[0]
    self.handler = user_plugin.ApiCreateUserClientApprovalHandler()

    self.args = user_plugin.ApiCreateUserClientApprovalArgs(
        client_id=self.client_id)
    self.args.approval.reason = self.token.reason
    self.args.approval.notified_users = ["approver"]
    self.args.approval.email_cc_addresses = ["test@example.com"]

    self.approval_urn = aff4.ROOT_URN.Add("ACL").Add(
        self.client_id.Basename()).Add(self.token.username).Add(
            utils.EncodeReasonString(self.token.reason))

    self.CreateUser("test")
    self.CreateUser("approver")

  def testCreatesAnApprovalWithGivenAttributes(self):
    with self.assertRaises(IOError):
      aff4.FACTORY.Open(self.approval_urn,
                        aff4_type=aff4_security.ClientApproval.__name__,
                        token=self.token)

    self.handler.Handle(self.args, token=self.token)

    fd = aff4.FACTORY.Open(self.approval_urn,
                           aff4_type=aff4_security.ClientApproval.__name__,
                           age=aff4.ALL_TIMES, token=self.token)
    self.assertEqual(fd.Get(fd.Schema.SUBJECT), self.client_id)
    self.assertEqual(fd.Get(fd.Schema.REASON), self.token.reason)
    self.assertEqual(fd.GetNonExpiredApprovers(), [self.token.username])
    self.assertEqual(fd.Get(fd.Schema.EMAIL_CC), "approver,test@example.com")

  def testApproversFromArgsAreIgnored(self):
    # It shouldn't be possible to specify list of approvers when creating
    # an approval. List of approvers contains names of GRR users who
    # approved the approval.
    self.args.approval.approvers = [self.token.username, "approver"]

    self.handler.Handle(self.args, token=self.token)

    fd = aff4.FACTORY.Open(self.approval_urn,
                           aff4_type=aff4_security.ClientApproval.__name__,
                           age=aff4.ALL_TIMES, token=self.token)
    self.assertEqual(fd.GetNonExpiredApprovers(), [self.token.username])

  def testRaisesOnEmptyReason(self):
    self.args.approval.reason = ""

    with self.assertRaises(ValueError):
      self.handler.Handle(self.args, token=self.token)

  def testNotifiesGrrUsers(self):
    self.handler.Handle(self.args, token=self.token)

    fd = aff4.FACTORY.Open("aff4:/users/approver",
                           aff4_type=aff4_users.GRRUser.__name__,
                           token=self.token)
    notifications = fd.ShowNotifications(reset=False)

    self.assertEqual(len(notifications), 1)

  def testSendsEmailsToGrrUsersAndCcAddresses(self):
    addresses = []
    def SendEmailStub(to_user, from_user, unused_subject, unused_message,
                      cc_addresses=None, **unused_kwargs):
      addresses.append((to_user, from_user, cc_addresses))

    with utils.Stubber(email_alerts.EMAIL_ALERTER, "SendEmail", SendEmailStub):
      self.handler.Handle(self.args, token=self.token)

    self.assertEqual(len(addresses), 1)
    self.assertEqual(addresses[0], ("approver", "test", "test@example.com"))


class ApiCreateUserClientApprovalHandlerRegressionTest(
    api_test_lib.ApiCallHandlerRegressionTest):
  """Regression test for ApiCreateUserClientApprovalHandler."""

  handler = "ApiCreateUserClientApprovalHandler"

  def Run(self):
    with test_lib.FakeTime(42):
      self.CreateUser("approver")

      client_id = self.SetupClients(1)[0]

      # Delete the certificate as it's being regenerated every time the
      # client is created.
      with aff4.FACTORY.Open(client_id, mode="rw",
                             token=self.token) as grr_client:
        grr_client.DeleteAttribute(grr_client.Schema.CERT)

    with test_lib.FakeTime(126):
      self.Check("POST", "/api/users/me/approvals/client/%s" %
                 client_id.Basename(),
                 {"approval": {
                     "reason": "really important reason!",
                     "notified_users": ["approver1", "approver2"],
                     "email_cc_addresses": ["test@example.com"]
                     }
                 })


class ApiListUserClientApprovalsHandlerTest(test_lib.GRRBaseTest):
  """Test for ApiListUserApprovalsHandler."""

  def setUp(self):
    super(ApiListUserClientApprovalsHandlerTest, self).setUp()
    self.client_id = self.SetupClients(1)[0]
    self.handler = user_plugin.ApiListUserClientApprovalsHandler()

  def testRendersRequestedClientApprovals(self):
    flow.GRRFlow.StartFlow(client_id=self.client_id,
                           flow_name="RequestClientApprovalFlow",
                           reason=self.token.reason,
                           subject_urn=self.client_id,
                           approver="approver",
                           token=self.token)

    args = user_plugin.ApiListUserClientApprovalsArgs()
    result = self.handler.Handle(args, token=self.token)

    self.assertEqual(len(result.items), 1)


class ApiListUserHuntApprovalsHandlerTest(test_lib.GRRBaseTest):
  """Test for ApiListUserHuntApprovalsHandler."""

  def setUp(self):
    super(ApiListUserHuntApprovalsHandlerTest, self).setUp()
    self.handler = user_plugin.ApiListUserHuntApprovalsHandler()

  def testRendersRequestedHuntAppoval(self):
    hunt_urn = aff4.ROOT_URN.Add("hunts").Add("H:ABCD1234")
    with aff4.FACTORY.Create(hunt_urn, aff4_type="AFF4Volume",
                             token=self.token) as _:
      pass

    flow.GRRFlow.StartFlow(flow_name="RequestHuntApprovalFlow",
                           reason=self.token.reason,
                           subject_urn=hunt_urn,
                           approver="approver",
                           token=self.token)

    args = user_plugin.ApiListUserHuntApprovalsArgs()
    result = self.handler.Render(args, token=self.token)

    self.assertEqual(len(result["items"]), 1)


class ApiListUserCronApprovalsHandlerTest(test_lib.GRRBaseTest):
  """Test for ApiListUserCronApprovalsHandler."""

  def setUp(self):
    super(ApiListUserCronApprovalsHandlerTest, self).setUp()
    self.handler = user_plugin.ApiListUserCronApprovalsHandler()

  def testRendersRequestedCronJobApproval(self):
    cron_urn = aff4.ROOT_URN.Add("cron").Add("CronJobFoo")
    with aff4.FACTORY.Create(cron_urn, aff4_type="AFF4Volume",
                             token=self.token) as _:
      pass

    flow.GRRFlow.StartFlow(flow_name="RequestCronJobApprovalFlow",
                           reason=self.token.reason,
                           subject_urn=cron_urn,
                           approver="approver",
                           token=self.token)

    args = user_plugin.ApiListUserCronApprovalsArgs()
    result = self.handler.Render(args, token=self.token)

    self.assertEqual(len(result["items"]), 1)


class ApiListUserClientApprovalsHandlerRegressionTest(
    api_test_lib.ApiCallHandlerRegressionTest):
  """Regression test for ApiListUserClientApprovalsHandlerTest."""

  handler = "ApiListUserClientApprovalsHandler"

  def Run(self):
    with test_lib.FakeTime(42):
      self.CreateAdminUser("approver")

      clients = self.SetupClients(2)
      for client_id in clients:
        # Delete the certificate as it's being regenerated every time the
        # client is created.
        with aff4.FACTORY.Open(client_id, mode="rw",
                               token=self.token) as grr_client:
          grr_client.DeleteAttribute(grr_client.Schema.CERT)

    with test_lib.FakeTime(44):
      flow.GRRFlow.StartFlow(client_id=clients[0],
                             flow_name="RequestClientApprovalFlow",
                             reason=self.token.reason,
                             subject_urn=clients[0],
                             approver="approver",
                             token=self.token)

    with test_lib.FakeTime(45):
      flow.GRRFlow.StartFlow(client_id=clients[1],
                             flow_name="RequestClientApprovalFlow",
                             reason=self.token.reason,
                             subject_urn=clients[1],
                             approver="approver",
                             token=self.token)

    with test_lib.FakeTime(84):
      approver_token = access_control.ACLToken(username="approver")
      flow.GRRFlow.StartFlow(client_id=clients[1],
                             flow_name="GrantClientApprovalFlow",
                             reason=self.token.reason,
                             delegate=self.token.username,
                             subject_urn=clients[1],
                             token=approver_token)

    with test_lib.FakeTime(126):
      self.Check("GET", "/api/users/me/approvals/client")


class ApiListUserHuntApprovalsHandlerRegressionTest(
    api_test_lib.ApiCallHandlerRegressionTest):
  """Regression test for ApiListUserClientApprovalsHandlerTest."""

  handler = "ApiListUserHuntApprovalsHandler"

  def Run(self):
    with test_lib.FakeTime(42):
      self.CreateAdminUser("approver")

      hunt = hunts.GRRHunt.StartHunt(
          hunt_name="GenericHunt", token=self.token)

    with test_lib.FakeTime(43):
      flow.GRRFlow.StartFlow(flow_name="RequestHuntApprovalFlow",
                             reason=self.token.reason,
                             subject_urn=hunt.urn,
                             approver="approver",
                             token=self.token)

    with test_lib.FakeTime(126):
      self.Check("GET", "/api/users/me/approvals/hunt",
                 replace={utils.SmartStr(hunt.urn.Basename()): "H:123456"})


class ApiGetUserSettingsHandlerTest(test_lib.GRRBaseTest):
  """Test for ApiGetUserSettingsHandler."""

  def setUp(self):
    super(ApiGetUserSettingsHandlerTest, self).setUp()
    self.handler = user_plugin.ApiGetUserSettingsHandler()

  def testRendersSettingsForUserCorrespondingToToken(self):
    with aff4.FACTORY.Create(
        aff4.ROOT_URN.Add("users").Add("foo"),
        aff4_type="GRRUser", mode="w", token=self.token) as user_fd:
      user_fd.Set(user_fd.Schema.GUI_SETTINGS,
                  aff4_users.GUISettings(mode="ADVANCED",
                                         canary_mode=True,
                                         docs_location="REMOTE"))

    result = self.handler.Render(None,
                                 token=access_control.ACLToken(username="foo"))
    self.assertEqual(result["value"]["mode"]["value"], "ADVANCED")
    self.assertEqual(result["value"]["canary_mode"]["value"], True)
    self.assertEqual(result["value"]["docs_location"]["value"], "REMOTE")


class ApiGetUserSettingsHandlerRegresstionTest(
    api_test_lib.ApiCallHandlerRegressionTest):
  """Regression test for ApiGetUserSettingsHandler."""

  handler = "ApiGetUserSettingsHandler"

  def Run(self):
    with test_lib.FakeTime(42):
      with aff4.FACTORY.Create(
          aff4.ROOT_URN.Add("users").Add(self.token.username),
          aff4_type="GRRUser", mode="w", token=self.token) as user_fd:
        user_fd.Set(user_fd.Schema.GUI_SETTINGS,
                    aff4_users.GUISettings(canary_mode=True))

    self.Check("GET", "/api/users/me/settings")


class ApiUpdateUserSettingsHandlerTest(test_lib.GRRBaseTest):
  """Tests for ApiUpdateUserSettingsHandler."""

  def setUp(self):
    super(ApiUpdateUserSettingsHandlerTest, self).setUp()
    self.handler = user_plugin.ApiUpdateUserSettingsHandler()

  def testSetsSettingsForUserCorrespondingToToken(self):
    settings = aff4_users.GUISettings(mode="ADVANCED",
                                      canary_mode=True,
                                      docs_location="REMOTE")

    # Render the request - effectively applying the settings for user "foo".
    result = self.handler.Render(settings,
                                 token=access_control.ACLToken(username="foo"))
    self.assertEqual(result["status"], "OK")

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
    self._SendNotification(notification_type="Discovery",
                           subject="<some client urn>",
                           message="<some message>",
                           client_id=self.client_id)
    self._SendNotification(notification_type="ViewObject",
                           subject=str(self.client_id),
                           message="<some other message>",
                           client_id=self.client_id)

    self.Check("GET", "/api/users/me/notifications/pending/count")


class ApiGetPendingUserNotificationsHandlerRegressionTest(
    api_test_lib.ApiCallHandlerRegressionTest):
  """Regression test for ApiGetPendingUserNotificationsHandler."""

  handler = "ApiGetPendingUserNotificationsHandler"

  def setUp(self):
    super(ApiGetPendingUserNotificationsHandlerRegressionTest,
          self).setUp()
    self.client_id = self.SetupClients(1)[0]

  def Run(self):
    with test_lib.FakeTime(42):
      self._SendNotification(notification_type="Discovery",
                             subject=str(self.client_id),
                             message="<some message>",
                             client_id=self.client_id)

    with test_lib.FakeTime(44):
      self._SendNotification(notification_type="ViewObject",
                             subject=str(self.client_id),
                             message="<some other message>",
                             client_id=self.client_id)

    base_url = "/api/users/me/notifications/pending"
    self.Check("GET", base_url)
    self.Check("GET", base_url + "?timestamp=43000000")


class ApiGetAndResetUserNotificationsHandlerRegressionTest(
    api_test_lib.ApiCallHandlerRegressionTest):
  """Regression test for ApiGetAndResetUserNotificationsHandler."""

  handler = "ApiGetAndResetUserNotificationsHandler"

  def setUp(self):
    super(ApiGetAndResetUserNotificationsHandlerRegressionTest, self).setUp()
    self.client_id = self.SetupClients(1)[0]

  def Run(self):
    with test_lib.FakeTime(42):
      self._SendNotification(notification_type="Discovery",
                             subject=str(self.client_id),
                             message="<some message>",
                             client_id=self.client_id)

    with test_lib.FakeTime(44):
      self._SendNotification(notification_type="ViewObject",
                             subject=str(self.client_id),
                             message="<some other message>",
                             client_id=self.client_id)

    # Notifications are pending in this request.
    self.Check("POST", "/api/users/me/notifications")

    # But not anymore in these requests.
    self.Check("POST", "/api/users/me/notifications?offset=1&count=1")
    self.Check("POST", "/api/users/me/notifications?filter=other")


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
