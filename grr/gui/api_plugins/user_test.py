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

from grr.lib.hunts import standard


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
    args = user_plugin.ApiGetUserClientApprovalArgs(client_id=self.client_id,
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

    args = user_plugin.ApiGetUserClientApprovalArgs(client_id=self.client_id,
                                                    reason="blah")
    result = self.handler.Handle(args, token=self.token)

    self.assertTrue(result.is_valid)
    self.assertEqual(
        sorted(result.approvers),
        sorted([approver_token.username, self.token.username]))

  def testRaisesWhenApprovalIsNotFound(self):
    args = user_plugin.ApiGetUserClientApprovalArgs(client_id=self.client_id,
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

    self.approval_urn = aff4.ROOT_URN.Add("ACL").Add(self.client_id.Basename(
    )).Add(self.token.username).Add(utils.EncodeReasonString(self.token.reason))

    self.CreateUser("test")
    self.CreateUser("approver")

  def testCreatesAnApprovalWithGivenAttributes(self):
    with self.assertRaises(IOError):
      aff4.FACTORY.Open(self.approval_urn,
                        aff4_type=aff4_security.ClientApproval,
                        token=self.token)

    self.handler.Handle(self.args, token=self.token)

    fd = aff4.FACTORY.Open(self.approval_urn,
                           aff4_type=aff4_security.ClientApproval,
                           age=aff4.ALL_TIMES,
                           token=self.token)
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
                           aff4_type=aff4_security.ClientApproval,
                           age=aff4.ALL_TIMES,
                           token=self.token)
    self.assertEqual(fd.GetNonExpiredApprovers(), [self.token.username])

  def testRaisesOnEmptyReason(self):
    self.args.approval.reason = ""

    with self.assertRaises(ValueError):
      self.handler.Handle(self.args, token=self.token)

  def testNotifiesGrrUsers(self):
    self.handler.Handle(self.args, token=self.token)

    fd = aff4.FACTORY.Open("aff4:/users/approver",
                           aff4_type=aff4_users.GRRUser,
                           token=self.token)
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
      self.Check("POST",
                 "/api/users/me/approvals/client/%s" % client_id.Basename(),
                 {"approval": {
                     "reason": "really important reason!",
                     "notified_users": ["approver1", "approver2"],
                     "email_cc_addresses": ["test@example.com"]
                 }})


class ApiListUserClientApprovalsHandlerTest(test_lib.GRRBaseTest):
  """Test for ApiListUserApprovalsHandler."""

  CLIENT_COUNT = 5

  def setUp(self):
    super(ApiListUserClientApprovalsHandlerTest, self).setUp()
    self.handler = user_plugin.ApiListUserClientApprovalsHandler()
    self.client_ids = self.SetupClients(self.CLIENT_COUNT)

  def _RequestClientApprovals(self):
    for client_id in self.client_ids:
      self.RequestClientApproval(client_id, token=self.token)

  def testRendersRequestedClientApprovals(self):
    self._RequestClientApprovals()

    args = user_plugin.ApiListUserClientApprovalsArgs()
    result = self.handler.Handle(args, token=self.token)

    # All approvals should be returned.
    self.assertEqual(len(result.items), self.CLIENT_COUNT)

  def testFiltersApprovalsByClientId(self):
    client_id = self.client_ids[0]

    self._RequestClientApprovals()

    # Get approvals for a specific client. There should be exactly one.
    args = user_plugin.ApiListUserClientApprovalsArgs(client_id=client_id)
    result = self.handler.Handle(args, token=self.token)

    self.assertEqual(len(result.items), 1)
    self.assertEqual(result.items[0].subject.urn, client_id)

  def testFiltersApprovalsByInvalidState(self):
    self._RequestClientApprovals()

    # We only requested approvals so far, so all of them should be invalid.
    args = user_plugin.ApiListUserClientApprovalsArgs(
        state=user_plugin.ApiListUserClientApprovalsArgs.State.INVALID)
    result = self.handler.Handle(args, token=self.token)

    self.assertEqual(len(result.items), self.CLIENT_COUNT)

    # Grant access to one client. Now all but one should be invalid.
    self.GrantClientApproval(self.client_ids[0],
                             self.token.username,
                             reason=self.token.reason)
    result = self.handler.Handle(args, token=self.token)
    self.assertEqual(len(result.items), self.CLIENT_COUNT - 1)

  def testFiltersApprovalsByValidState(self):
    self._RequestClientApprovals()

    # We only requested approvals so far, so none of them is valid.
    args = user_plugin.ApiListUserClientApprovalsArgs(
        state=user_plugin.ApiListUserClientApprovalsArgs.State.VALID)
    result = self.handler.Handle(args, token=self.token)

    # We do not have any approved approvals yet.
    self.assertEqual(len(result.items), 0)

    # Grant access to one client. Now exactly one approval should be valid.
    self.GrantClientApproval(self.client_ids[0],
                             self.token.username,
                             reason=self.token.reason)
    result = self.handler.Handle(args, token=self.token)
    self.assertEqual(len(result.items), 1)
    self.assertEqual(result.items[0].subject.urn, self.client_ids[0])

  def testFiltersApprovalsByClientIdAndState(self):
    client_id = self.client_ids[0]

    self._RequestClientApprovals()

    # Grant approval to a certain client.
    self.GrantClientApproval(client_id,
                             self.token.username,
                             reason=self.token.reason)

    args = user_plugin.ApiListUserClientApprovalsArgs(
        client_id=client_id,
        state=user_plugin.ApiListUserClientApprovalsArgs.State.VALID)
    result = self.handler.Handle(args, token=self.token)

    # We have a valid approval for the requested client.
    self.assertEqual(len(result.items), 1)

    args.state = user_plugin.ApiListUserClientApprovalsArgs.State.INVALID
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

    args = user_plugin.ApiListUserClientApprovalsArgs(client_id=client_id,
                                                      offset=0,
                                                      count=5)
    result = self.handler.Handle(args, token=self.token)

    # Approvals are returned newest to oldest, so the first five approvals
    # have reason 9 to 5.
    self.assertEqual(len(result.items), 5)
    for item, i in zip(result.items, reversed(range(6, 10))):
      self.assertEqual(item.reason, "Request reason %d" % i)

    # When no count is specified, take all items from offset to the end.
    args = user_plugin.ApiListUserClientApprovalsArgs(client_id=client_id,
                                                      offset=7)
    result = self.handler.Handle(args, token=self.token)

    self.assertEqual(len(result.items), 4)
    for item, i in zip(result.items, reversed(range(0, 4))):
      self.assertEqual(item.reason, "Request reason %d" % i)


class ApiListUserHuntApprovalsHandlerTest(test_lib.GRRBaseTest):
  """Test for ApiListUserHuntApprovalsHandler."""

  def setUp(self):
    super(ApiListUserHuntApprovalsHandlerTest, self).setUp()
    self.handler = user_plugin.ApiListUserHuntApprovalsHandler()

  def testRendersRequestedHuntAppoval(self):
    with hunts.GRRHunt.StartHunt(hunt_name=standard.SampleHunt.__name__,
                                 token=self.token) as hunt:
      pass

    flow.GRRFlow.StartFlow(flow_name="RequestHuntApprovalFlow",
                           reason=self.token.reason,
                           subject_urn=hunt.urn,
                           approver="approver",
                           token=self.token)

    args = user_plugin.ApiListUserHuntApprovalsArgs()
    result = self.handler.Handle(args, token=self.token)

    self.assertEqual(len(result.items), 1)


class ApiListUserCronApprovalsHandlerTest(test_lib.GRRBaseTest):
  """Test for ApiListUserCronApprovalsHandler."""

  def setUp(self):
    super(ApiListUserCronApprovalsHandlerTest, self).setUp()
    self.handler = user_plugin.ApiListUserCronApprovalsHandler()

  def testRendersRequestedCronJobApproval(self):
    cron_manager = aff4_cronjobs.CronManager()
    cron_args = aff4_cronjobs.CreateCronJobFlowArgs(periodicity="1d",
                                                    allow_overruns=False)
    cron_job_urn = cron_manager.ScheduleFlow(cron_args=cron_args,
                                             token=self.token)

    flow.GRRFlow.StartFlow(flow_name="RequestCronJobApprovalFlow",
                           reason=self.token.reason,
                           subject_urn=cron_job_urn,
                           approver="approver",
                           token=self.token)

    args = user_plugin.ApiListUserCronApprovalsArgs()
    result = self.handler.Handle(args, token=self.token)

    self.assertEqual(len(result.items), 1)


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
      self.Check("GET",
                 "/api/users/me/approvals/client/%s" % (clients[0].Basename()))


class ApiListUserHuntApprovalsHandlerRegressionTest(
    api_test_lib.ApiCallHandlerRegressionTest):
  """Regression test for ApiListUserClientApprovalsHandlerTest."""

  handler = "ApiListUserHuntApprovalsHandler"

  def Run(self):
    with test_lib.FakeTime(42):
      self.CreateAdminUser("approver")

      hunt = hunts.GRRHunt.StartHunt(hunt_name="GenericHunt", token=self.token)

    with test_lib.FakeTime(43):
      flow.GRRFlow.StartFlow(flow_name="RequestHuntApprovalFlow",
                             reason=self.token.reason,
                             subject_urn=hunt.urn,
                             approver="approver",
                             token=self.token)

    with test_lib.FakeTime(126):
      self.Check("GET",
                 "/api/users/me/approvals/hunt",
                 replace={utils.SmartStr(hunt.urn.Basename()): "H:123456"})


class ApiGetGrrUserHandlerTest(test_lib.GRRBaseTest):
  """Test for ApiGetUserSettingsHandler."""

  def setUp(self):
    super(ApiGetGrrUserHandlerTest, self).setUp()
    self.handler = user_plugin.ApiGetGrrUserHandler()

  def testRendersObjectForNonExistingUser(self):
    result = self.handler.Handle(None,
                                 token=access_control.ACLToken(username="foo"))
    self.assertEqual(result.username, "foo")

  def testRendersSettingsForUserCorrespondingToToken(self):
    with aff4.FACTORY.Create(
        aff4.ROOT_URN.Add("users").Add("foo"),
        aff4_type=aff4_users.GRRUser,
        mode="w",
        token=self.token) as user_fd:
      user_fd.Set(user_fd.Schema.GUI_SETTINGS,
                  aff4_users.GUISettings(mode="ADVANCED",
                                         canary_mode=True,
                                         docs_location="REMOTE"))

    result = self.handler.Handle(None,
                                 token=access_control.ACLToken(username="foo"))
    self.assertEqual(result.settings.mode, "ADVANCED")
    self.assertEqual(result.settings.canary_mode, True)
    self.assertEqual(result.settings.docs_location, "REMOTE")

  def testRendersTraitsPassedInConstructor(self):
    result = self.handler.Handle(None,
                                 token=access_control.ACLToken(username="foo"))
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
    settings = aff4_users.GUISettings(mode="ADVANCED",
                                      canary_mode=True,
                                      docs_location="REMOTE")
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
    self._SendNotification(notification_type="Discovery",
                           subject="<some client urn>",
                           message="<some message>",
                           client_id=self.client_id)
    self._SendNotification(notification_type="ViewObject",
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
      self._SendNotification(notification_type="Discovery",
                             subject=str(self.client_id),
                             message="<some message>",
                             client_id=self.client_id)

      self._SendNotification(notification_type="Discovery",
                             subject=str(self.client_id),
                             message="<some message with identical time>",
                             client_id=self.client_id)

    with test_lib.FakeTime(self.TIME_1):
      self._SendNotification(notification_type="ViewObject",
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


class ApiListPendingGlobalNotificationsHandlerRegressionTest(
    api_test_lib.ApiCallHandlerRegressionTest):
  """Regression test for ApiListPendingGlobalNotificationsHandler."""

  handler = "ApiListPendingGlobalNotificationsHandler"

  # Global notifications are only shown in a certain time interval. By default,
  # this is from the moment they are created until two weeks later. Create
  # a notification that is too old to be returned and two valid ones.
  NOW = rdfvalue.RDFDatetime().Now()
  TIME_TOO_EARLY = NOW - rdfvalue.Duration("4w")
  TIME_0 = NOW - rdfvalue.Duration("12h")
  TIME_1 = NOW - rdfvalue.Duration("1h")

  def setUp(self):
    super(ApiListPendingGlobalNotificationsHandlerRegressionTest, self).setUp()

  def Run(self):
    with aff4.FACTORY.Create(aff4_users.GlobalNotificationStorage.DEFAULT_PATH,
                             aff4_type=aff4_users.GlobalNotificationStorage,
                             mode="rw",
                             token=self.token) as storage:
      storage.AddNotification(aff4_users.GlobalNotification(
          type=aff4_users.GlobalNotification.Type.ERROR,
          header="Oh no, we're doomed!",
          content="Houston, Houston, we have a prob...",
          link="http://www.google.com",
          show_from=self.TIME_0))

      storage.AddNotification(aff4_users.GlobalNotification(
          type=aff4_users.GlobalNotification.Type.INFO,
          header="Nothing to worry about!",
          link="http://www.google.com",
          show_from=self.TIME_1))

      storage.AddNotification(aff4_users.GlobalNotification(
          type=aff4_users.GlobalNotification.Type.WARNING,
          header="Nothing to worry, we won't see this!",
          link="http://www.google.com",
          show_from=self.TIME_TOO_EARLY))

    replace = {("%d" % self.TIME_0.AsMicroSecondsFromEpoch()): "0",
               ("%d" % self.TIME_1.AsMicroSecondsFromEpoch()): "0"}

    self.Check("GET",
               "/api/users/me/notifications/pending/global",
               replace=replace)


class ApiDeletePendingGlobalNotificationHandlerTest(test_lib.GRRBaseTest):
  """Test for ApiDeletePendingGlobalNotificationHandler."""

  def setUp(self):
    super(ApiDeletePendingGlobalNotificationHandlerTest, self).setUp()
    self.handler = user_plugin.ApiDeletePendingGlobalNotificationHandler()

    with aff4.FACTORY.Create(aff4_users.GlobalNotificationStorage.DEFAULT_PATH,
                             aff4_type=aff4_users.GlobalNotificationStorage,
                             mode="rw",
                             token=self.token) as storage:
      storage.AddNotification(aff4_users.GlobalNotification(
          type=aff4_users.GlobalNotification.Type.ERROR,
          header="Oh no, we're doomed!",
          content="Houston, Houston, we have a prob...",
          link="http://www.google.com"))
      storage.AddNotification(aff4_users.GlobalNotification(
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
