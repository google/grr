#!/usr/bin/env python
"""This module contains tests for user API handlers."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


from builtins import range  # pylint: disable=redefined-builtin
from builtins import zip  # pylint: disable=redefined-builtin

from grr_response_core.lib import flags
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.lib.util import compatibility
from grr_response_server import access_control
from grr_response_server import aff4
from grr_response_server import data_store
from grr_response_server import email_alerts
from grr_response_server import notification
from grr_response_server.aff4_objects import cronjobs as aff4_cronjobs
from grr_response_server.aff4_objects import users as aff4_users
from grr_response_server.gui import api_call_handler_base
from grr_response_server.gui import api_test_lib

from grr_response_server.gui.api_plugins import user as user_plugin
from grr_response_server.hunts import implementation
from grr_response_server.hunts import standard

from grr_response_server.rdfvalues import cronjobs as rdf_cronjobs
from grr_response_server.rdfvalues import objects as rdf_objects

from grr.test_lib import acl_test_lib
from grr.test_lib import db_test_lib
from grr.test_lib import hunt_test_lib
from grr.test_lib import notification_test_lib
from grr.test_lib import test_lib


@db_test_lib.DualDBTest
class ApiNotificationTest(acl_test_lib.AclTestMixin,
                          notification_test_lib.NotificationTestMixin,
                          api_test_lib.ApiCallHandlerTest):
  """Tests for ApiNotification class."""

  def setUp(self):
    super(ApiNotificationTest, self).setUp()
    self.client_id = self.SetupClient(0)

  def InitFromObj_(self, notification_type, reference, message=None):
    self.CreateUser(self.token.username)
    notification.Notify(self.token.username, notification_type, message or "",
                        reference)
    ns = self.GetUserNotifications(self.token.username)

    if data_store.RelationalDBReadEnabled():
      # Treat the notification as an object coming from REL_DB.
      return user_plugin.ApiNotification().InitFromUserNotification(ns[0])
    else:
      # Treat the notification as an old-style notification object.
      return user_plugin.ApiNotification().InitFromNotification(ns[0])

  def testDiscoveryNotificationIsParsedCorrectly(self):
    n = self.InitFromObj_(
        rdf_objects.UserNotification.Type.TYPE_CLIENT_INTERROGATED,
        rdf_objects.ObjectReference(
            reference_type=rdf_objects.ObjectReference.Type.CLIENT,
            client=rdf_objects.ClientReference(
                client_id=self.client_id.Basename())))

    self.assertEqual(n.reference.type, "CLIENT")
    self.assertEqual(n.reference.client.client_id.ToClientURN(), self.client_id)

  def testClientApprovalGrantedNotificationIsParsedCorrectly(self):
    n = self.InitFromObj_(
        rdf_objects.UserNotification.Type.TYPE_CLIENT_APPROVAL_GRANTED,
        rdf_objects.ObjectReference(
            reference_type=rdf_objects.ObjectReference.Type.CLIENT,
            client=rdf_objects.ClientReference(
                client_id=self.client_id.Basename())))

    self.assertEqual(n.reference.type, "CLIENT")
    self.assertEqual(n.reference.client.client_id.ToClientURN(), self.client_id)

  def testHuntNotificationIsParsedCorrectly(self):
    n = self.InitFromObj_(
        rdf_objects.UserNotification.Type.TYPE_HUNT_STOPPED,
        rdf_objects.ObjectReference(
            reference_type=rdf_objects.ObjectReference.Type.HUNT,
            hunt=rdf_objects.HuntReference(hunt_id="H:123456")))

    self.assertEqual(n.reference.type, "HUNT")
    self.assertEqual(n.reference.hunt.hunt_id, "H:123456")

  def testCronNotificationIsParsedCorrectly(self):
    n = self.InitFromObj_(
        rdf_objects.UserNotification.Type.TYPE_CRON_JOB_APPROVAL_GRANTED,
        rdf_objects.ObjectReference(
            reference_type=rdf_objects.ObjectReference.Type.CRON_JOB,
            cron_job=rdf_objects.CronJobReference(cron_job_id="FooBar")))

    self.assertEqual(n.reference.type, "CRON")
    self.assertEqual(n.reference.cron.cron_job_id, "FooBar")

  def testFlowSuccessNotificationIsParsedCorrectly(self):
    n = self.InitFromObj_(
        rdf_objects.UserNotification.Type.TYPE_FLOW_RUN_COMPLETED,
        rdf_objects.ObjectReference(
            reference_type=rdf_objects.ObjectReference.Type.FLOW,
            flow=rdf_objects.FlowReference(
                client_id=self.client_id.Basename(), flow_id="F:123456")))

    self.assertEqual(n.reference.type, "FLOW")
    self.assertEqual(n.reference.flow.client_id.ToClientURN(), self.client_id)
    self.assertEqual(n.reference.flow.flow_id, "F:123456")

  def testFlowFailureNotificationIsParsedCorrectly(self):
    n = self.InitFromObj_(
        rdf_objects.UserNotification.Type.TYPE_FLOW_RUN_FAILED,
        rdf_objects.ObjectReference(
            reference_type=rdf_objects.ObjectReference.Type.FLOW,
            flow=rdf_objects.FlowReference(
                client_id=self.client_id.Basename(), flow_id="F:123456")))

    self.assertEqual(n.reference.type, "FLOW")
    self.assertEqual(n.reference.flow.client_id.ToClientURN(), self.client_id)
    self.assertEqual(n.reference.flow.flow_id, "F:123456")

  def testVfsNotificationIsParsedCorrectly(self):
    n = self.InitFromObj_(
        rdf_objects.UserNotification.Type.TYPE_VFS_FILE_COLLECTED,
        rdf_objects.ObjectReference(
            reference_type=rdf_objects.ObjectReference.Type.VFS_FILE,
            vfs_file=rdf_objects.VfsFileReference(
                client_id=self.client_id.Basename(),
                path_type=rdf_objects.PathInfo.PathType.OS,
                path_components=["foo", "bar"])))

    self.assertEqual(n.reference.type, "VFS")
    self.assertEqual(n.reference.vfs.client_id.ToClientURN(), self.client_id)
    self.assertEqual(n.reference.vfs.vfs_path, "fs/os/foo/bar")

  def testClientApprovalNotificationIsParsedCorrectly(self):
    n = self.InitFromObj_(
        rdf_objects.UserNotification.Type.TYPE_CLIENT_APPROVAL_REQUESTED,
        rdf_objects.ObjectReference(
            reference_type=rdf_objects.ObjectReference.Type.APPROVAL_REQUEST,
            approval_request=rdf_objects.ApprovalRequestReference(
                approval_type=rdf_objects.ApprovalRequest.ApprovalType
                .APPROVAL_TYPE_CLIENT,
                approval_id="foo-bar",
                subject_id=self.client_id.Basename(),
                requestor_username=self.token.username)))

    self.assertEqual(n.reference.type, "CLIENT_APPROVAL")

    client_approval = n.reference.client_approval
    self.assertEqual(client_approval.client_id.ToClientURN(), self.client_id)
    self.assertEqual(client_approval.username, self.token.username)
    self.assertEqual(client_approval.approval_id, "foo-bar")

  def testHuntApprovalNotificationIsParsedCorrectly(self):
    n = self.InitFromObj_(
        rdf_objects.UserNotification.Type.TYPE_HUNT_APPROVAL_REQUESTED,
        rdf_objects.ObjectReference(
            reference_type=rdf_objects.ObjectReference.Type.APPROVAL_REQUEST,
            approval_request=rdf_objects.ApprovalRequestReference(
                approval_type=rdf_objects.ApprovalRequest.ApprovalType
                .APPROVAL_TYPE_HUNT,
                approval_id="foo-bar",
                subject_id="H:123456",
                requestor_username=self.token.username)))

    self.assertEqual(n.reference.type, "HUNT_APPROVAL")
    self.assertEqual(n.reference.hunt_approval.hunt_id, "H:123456")
    self.assertEqual(n.reference.hunt_approval.username, self.token.username)
    self.assertEqual(n.reference.hunt_approval.approval_id, "foo-bar")

  def testCronJobApprovalNotificationIsParsedCorrectly(self):
    n = self.InitFromObj_(
        rdf_objects.UserNotification.Type.TYPE_CRON_JOB_APPROVAL_REQUESTED,
        rdf_objects.ObjectReference(
            reference_type=rdf_objects.ObjectReference.Type.APPROVAL_REQUEST,
            approval_request=rdf_objects.ApprovalRequestReference(
                approval_type=rdf_objects.ApprovalRequest.ApprovalType
                .APPROVAL_TYPE_CRON_JOB,
                approval_id="foo-bar",
                subject_id="FooBar",
                requestor_username=self.token.username)))

    self.assertEqual(n.reference.type, "CRON_JOB_APPROVAL")
    self.assertEqual(n.reference.cron_job_approval.cron_job_id, "FooBar")
    self.assertEqual(n.reference.cron_job_approval.username,
                     self.token.username)
    self.assertEqual(n.reference.cron_job_approval.approval_id, "foo-bar")

  def testFileArchiveGenerationFailedNotificationIsParsedAsUnknownOrUnset(self):
    n = self.InitFromObj_(
        rdf_objects.UserNotification.Type.TYPE_FILE_ARCHIVE_GENERATION_FAILED,
        None,
        message="blah")
    self.assertIn(n.reference.type, ["UNSET", "UNKNOWN"])
    self.assertEqual(n.message, "blah")

  def testVfsListDirectoryCompletedIsParsedCorrectly(self):
    n = self.InitFromObj_(
        rdf_objects.UserNotification.Type.TYPE_VFS_LIST_DIRECTORY_COMPLETED,
        rdf_objects.ObjectReference(
            reference_type=rdf_objects.ObjectReference.Type.VFS_FILE,
            vfs_file=rdf_objects.VfsFileReference(
                client_id=self.client_id.Basename(),
                path_type=rdf_objects.PathInfo.PathType.OS,
                path_components=["foo", "bar"])))

    self.assertEqual(n.reference.type, "VFS")
    self.assertEqual(n.reference.vfs.client_id.ToClientURN(), self.client_id)
    self.assertEqual(n.reference.vfs.vfs_path, "fs/os/foo/bar")

  def testUnknownNotificationIsParsedCorrectly(self):
    n = user_plugin.ApiNotification().InitFromNotification(
        rdf_flows.Notification(
            type="ViewObject", subject=self.client_id.Add("foo/bar")))
    self.assertEqual(n.reference.type, "UNKNOWN")
    self.assertEqual(n.reference.unknown.subject_urn,
                     self.client_id.Add("foo/bar"))

    n = user_plugin.ApiNotification().InitFromNotification(
        rdf_flows.Notification(type="FlowStatus", subject="foo/bar"))
    self.assertEqual(n.reference.type, "UNKNOWN")
    self.assertEqual(n.reference.unknown.subject_urn, "foo/bar")

  def testNotificationWithoutSubject(self):
    n = user_plugin.ApiNotification().InitFromNotification(
        rdf_flows.Notification(type="ViewObject"))
    self.assertEqual(n.reference.type, "UNKNOWN")


class ApiCreateApprovalHandlerTestMixin(
    notification_test_lib.NotificationTestMixin, acl_test_lib.AclTestMixin):
  """Base class for tests testing Create*ApprovalHandlers."""

  def SetUpApprovalTest(self):
    self.CreateUser(u"test")
    self.CreateUser(u"approver")

    self.handler = None
    self.args = None

  def ReadApproval(self, approval_id):
    raise NotImplementedError()

  def testCreatesAnApprovalWithGivenAttributes(self):
    approval_id = self.handler.Handle(self.args, token=self.token).id
    approval_obj = self.ReadApproval(approval_id)

    self.assertEqual(approval_obj.reason, self.token.reason)
    self.assertEqual(approval_obj.approvers, [self.token.username])
    self.assertEqual(approval_obj.email_cc_addresses, ["test@example.com"])

  def testApproversFromArgsAreIgnored(self):
    # It shouldn't be possible to specify list of approvers when creating
    # an approval. List of approvers contains names of GRR users who
    # approved the approval.
    self.args.approval.approvers = [self.token.username, u"approver"]

    approval_id = self.handler.Handle(self.args, token=self.token).id
    approval_obj = self.ReadApproval(approval_id)

    self.assertEqual(approval_obj.approvers, [self.token.username])

  def testRaisesOnEmptyReason(self):
    self.args.approval.reason = ""

    with self.assertRaises(ValueError):
      self.handler.Handle(self.args, token=self.token)

  def testNotifiesGrrUsers(self):
    self.handler.Handle(self.args, token=self.token)

    notifications = self.GetUserNotifications(u"approver")
    self.assertLen(notifications, 1)

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

    self.assertLen(addresses, 1)
    self.assertEqual(addresses[0],
                     (u"approver", self.token.username, "test@example.com"))


@db_test_lib.DualDBTest
class ApiGetClientApprovalHandlerTest(acl_test_lib.AclTestMixin,
                                      api_test_lib.ApiCallHandlerTest):
  """Test for ApiGetClientApprovalHandler."""

  def setUp(self):
    super(ApiGetClientApprovalHandlerTest, self).setUp()
    self.client_id = self.SetupClient(0)
    self.handler = user_plugin.ApiGetClientApprovalHandler()

  def testRendersRequestedClientApproval(self):
    approval_id = self.RequestClientApproval(
        self.client_id.Basename(),
        requestor=self.token.username,
        reason="blah",
        approver=u"approver",
        email_cc_address="test@example.com")

    args = user_plugin.ApiGetClientApprovalArgs(
        client_id=self.client_id,
        approval_id=approval_id,
        username=self.token.username)
    result = self.handler.Handle(args, token=self.token)

    self.assertEqual(result.subject.client_id.ToClientURN(), self.client_id)
    self.assertEqual(result.reason, "blah")
    self.assertEqual(result.is_valid, False)
    self.assertEqual(result.is_valid_message,
                     "Need at least 1 additional approver for access.")

    self.assertEqual(result.notified_users, [u"approver"])
    self.assertEqual(result.email_cc_addresses, ["test@example.com"])

    # Every approval is self-approved by default.
    self.assertEqual(result.approvers, [self.token.username])

  def testIncludesApproversInResultWhenApprovalIsGranted(self):
    approval_id = self.RequestAndGrantClientApproval(
        self.client_id.Basename(),
        reason=u"blah",
        approver=u"approver",
        requestor=self.token.username)

    args = user_plugin.ApiGetClientApprovalArgs(
        client_id=self.client_id,
        approval_id=approval_id,
        username=self.token.username)
    result = self.handler.Handle(args, token=self.token)

    self.assertTrue(result.is_valid)
    self.assertEqual(
        sorted(result.approvers), sorted([self.token.username, u"approver"]))

  def testRaisesWhenApprovalIsNotFound(self):
    args = user_plugin.ApiGetClientApprovalArgs(
        client_id=self.client_id,
        approval_id="approval:112233",
        username=self.token.username)

    with self.assertRaises(api_call_handler_base.ResourceNotFoundError):
      self.handler.Handle(args, token=self.token)


@db_test_lib.DualDBTest
class ApiCreateClientApprovalHandlerTest(api_test_lib.ApiCallHandlerTest,
                                         ApiCreateApprovalHandlerTestMixin):
  """Test for ApiCreateClientApprovalHandler."""

  def ReadApproval(self, approval_id):
    approvals = self.ListClientApprovals(requestor=self.token.username)
    self.assertLen(approvals, 1)
    self.assertEqual(approvals[0].id, approval_id)
    return approvals[0]

  def setUp(self):
    super(ApiCreateClientApprovalHandlerTest, self).setUp()

    self.SetUpApprovalTest()

    self.subject_urn = client_id = self.SetupClient(0)

    self.handler = user_plugin.ApiCreateClientApprovalHandler()

    self.args = user_plugin.ApiCreateClientApprovalArgs(client_id=client_id)
    self.args.approval.reason = self.token.reason
    self.args.approval.notified_users = [u"approver"]
    self.args.approval.email_cc_addresses = ["test@example.com"]

  def testKeepAliveFlowIsStartedWhenFlagIsSet(self):
    self.args.keep_client_alive = True

    self.handler.Handle(self.args, self.token)

    if data_store.RelationalDBFlowsEnabled():
      flows = data_store.REL_DB.ReadAllFlowObjects(unicode(self.args.client_id))
    else:
      flows = aff4.FACTORY.Open(
          self.subject_urn.Add("flows"), token=self.token).OpenChildren()
      keep_alive_flow = [
          f for f in flows if compatibility.GetName(f.__class__) == "KeepAlive"
      ]
      self.assertLen(keep_alive_flow, 1)


@db_test_lib.DualDBTest
class ApiListClientApprovalsHandlerTest(api_test_lib.ApiCallHandlerTest,
                                        acl_test_lib.AclTestMixin):
  """Test for ApiListApprovalsHandler."""

  CLIENT_COUNT = 5

  def setUp(self):
    super(ApiListClientApprovalsHandlerTest, self).setUp()
    self.handler = user_plugin.ApiListClientApprovalsHandler()
    self.client_ids = self.SetupClients(self.CLIENT_COUNT)

  def _RequestClientApprovals(self):
    approval_ids = []
    for client_id in self.client_ids:
      approval_ids.append(self.RequestClientApproval(client_id.Basename()))
    return approval_ids

  def testRendersRequestedClientApprovals(self):
    self._RequestClientApprovals()

    args = user_plugin.ApiListClientApprovalsArgs()
    result = self.handler.Handle(args, token=self.token)

    # All approvals should be returned.
    self.assertLen(result.items, self.CLIENT_COUNT)

  def testFiltersApprovalsByClientId(self):
    client_id = self.client_ids[0]

    self._RequestClientApprovals()

    # Get approvals for a specific client. There should be exactly one.
    args = user_plugin.ApiListClientApprovalsArgs(client_id=client_id)
    result = self.handler.Handle(args, token=self.token)

    self.assertLen(result.items, 1)
    self.assertEqual(result.items[0].subject.client_id.ToClientURN(), client_id)

  def testFiltersApprovalsByInvalidState(self):
    approval_ids = self._RequestClientApprovals()

    # We only requested approvals so far, so all of them should be invalid.
    args = user_plugin.ApiListClientApprovalsArgs(
        state=user_plugin.ApiListClientApprovalsArgs.State.INVALID)
    result = self.handler.Handle(args, token=self.token)

    self.assertLen(result.items, self.CLIENT_COUNT)

    # Grant access to one client. Now all but one should be invalid.
    self.GrantClientApproval(
        self.client_ids[0],
        requestor=self.token.username,
        approval_id=approval_ids[0])
    result = self.handler.Handle(args, token=self.token)
    self.assertLen(result.items, self.CLIENT_COUNT - 1)

  def testFiltersApprovalsByValidState(self):
    approval_ids = self._RequestClientApprovals()

    # We only requested approvals so far, so none of them is valid.
    args = user_plugin.ApiListClientApprovalsArgs(
        state=user_plugin.ApiListClientApprovalsArgs.State.VALID)
    result = self.handler.Handle(args, token=self.token)

    # We do not have any approved approvals yet.
    self.assertEmpty(result.items)

    # Grant access to one client. Now exactly one approval should be valid.
    self.GrantClientApproval(
        self.client_ids[0].Basename(),
        requestor=self.token.username,
        approval_id=approval_ids[0])
    result = self.handler.Handle(args, token=self.token)
    self.assertLen(result.items, 1)
    self.assertEqual(result.items[0].subject.client_id.ToClientURN(),
                     self.client_ids[0])

  def testFiltersApprovalsByClientIdAndState(self):
    client_id = self.client_ids[0]

    approval_ids = self._RequestClientApprovals()

    # Grant approval to a certain client.
    self.GrantClientApproval(
        client_id.Basename(),
        requestor=self.token.username,
        approval_id=approval_ids[0])

    args = user_plugin.ApiListClientApprovalsArgs(
        client_id=client_id,
        state=user_plugin.ApiListClientApprovalsArgs.State.VALID)
    result = self.handler.Handle(args, token=self.token)

    # We have a valid approval for the requested client.
    self.assertLen(result.items, 1)

    args.state = user_plugin.ApiListClientApprovalsArgs.State.INVALID
    result = self.handler.Handle(args, token=self.token)

    # However, we do not have any invalid approvals for the client.
    self.assertEmpty(result.items)

  def testFilterConsidersOffsetAndCount(self):
    client_id = self.client_ids[0]

    # Create five approval requests without granting them.
    for i in range(10):
      with test_lib.FakeTime(42 + i):
        self.RequestClientApproval(
            client_id.Basename(), reason="Request reason %d" % i)

    args = user_plugin.ApiListClientApprovalsArgs(
        client_id=client_id, offset=0, count=5)
    result = self.handler.Handle(args, token=self.token)

    # Approvals are returned newest to oldest, so the first five approvals
    # have reason 9 to 5.
    self.assertLen(result.items, 5)
    for item, i in zip(result.items, reversed(range(6, 10))):
      self.assertEqual(item.reason, "Request reason %d" % i)

    # When no count is specified, take all items from offset to the end.
    args = user_plugin.ApiListClientApprovalsArgs(client_id=client_id, offset=7)
    result = self.handler.Handle(args, token=self.token)

    self.assertLen(result.items, 3)
    for item, i in zip(result.items, reversed(range(0, 3))):
      self.assertEqual(item.reason, "Request reason %d" % i)


@db_test_lib.DualDBTest
class ApiCreateHuntApprovalHandlerTest(api_test_lib.ApiCallHandlerTest,
                                       ApiCreateApprovalHandlerTestMixin,
                                       hunt_test_lib.StandardHuntTestMixin):
  """Test for ApiCreateHuntApprovalHandler."""

  def ReadApproval(self, approval_id):
    approvals = self.ListHuntApprovals(requestor=self.token.username)
    self.assertLen(approvals, 1)
    self.assertEqual(approvals[0].id, approval_id)
    return approvals[0]

  def setUp(self):
    super(ApiCreateHuntApprovalHandlerTest, self).setUp()

    self.SetUpApprovalTest()

    with self.CreateHunt(description="foo") as hunt_obj:
      hunt_id = hunt_obj.urn.Basename()

    self.handler = user_plugin.ApiCreateHuntApprovalHandler()

    self.args = user_plugin.ApiCreateHuntApprovalArgs(hunt_id=hunt_id)
    self.args.approval.reason = self.token.reason
    self.args.approval.notified_users = ["approver"]
    self.args.approval.email_cc_addresses = ["test@example.com"]


@db_test_lib.DualDBTest
class ApiListHuntApprovalsHandlerTest(acl_test_lib.AclTestMixin,
                                      api_test_lib.ApiCallHandlerTest):
  """Test for ApiListHuntApprovalsHandler."""

  def setUp(self):
    super(ApiListHuntApprovalsHandlerTest, self).setUp()
    self.handler = user_plugin.ApiListHuntApprovalsHandler()

  def testRendersRequestedHuntAppoval(self):
    with implementation.StartHunt(
        hunt_name=standard.SampleHunt.__name__, token=self.token) as hunt:
      pass

    self.RequestHuntApproval(
        hunt.urn.Basename(),
        reason=self.token.reason,
        approver=u"approver",
        requestor=self.token.username)

    args = user_plugin.ApiListHuntApprovalsArgs()
    result = self.handler.Handle(args, token=self.token)

    self.assertLen(result.items, 1)


@db_test_lib.DualDBTest
class ApiCreateCronJobApprovalHandlerTest(
    ApiCreateApprovalHandlerTestMixin,
    api_test_lib.ApiCallHandlerTest,
):
  """Test for ApiCreateCronJobApprovalHandler."""

  def ReadApproval(self, approval_id):
    approvals = self.ListCronJobApprovals(requestor=self.token.username)
    self.assertLen(approvals, 1)
    self.assertEqual(approvals[0].id, approval_id)
    return approvals[0]

  def setUp(self):
    super(ApiCreateCronJobApprovalHandlerTest, self).setUp()

    self.SetUpApprovalTest()

    cron_manager = aff4_cronjobs.GetCronManager()
    cron_args = rdf_cronjobs.CreateCronJobArgs(
        frequency="1d", allow_overruns=False)
    cron_id = cron_manager.CreateJob(cron_args=cron_args, token=self.token)

    self.handler = user_plugin.ApiCreateCronJobApprovalHandler()

    self.args = user_plugin.ApiCreateCronJobApprovalArgs(cron_job_id=cron_id)
    self.args.approval.reason = self.token.reason
    self.args.approval.notified_users = [u"approver"]
    self.args.approval.email_cc_addresses = ["test@example.com"]


@db_test_lib.DualDBTest
class ApiListCronJobApprovalsHandlerTest(acl_test_lib.AclTestMixin,
                                         api_test_lib.ApiCallHandlerTest):
  """Test for ApiListCronJobApprovalsHandler."""

  def setUp(self):
    super(ApiListCronJobApprovalsHandlerTest, self).setUp()
    self.handler = user_plugin.ApiListCronJobApprovalsHandler()

  def testRendersRequestedCronJobApproval(self):
    cron_manager = aff4_cronjobs.GetCronManager()
    cron_args = rdf_cronjobs.CreateCronJobArgs(
        frequency="1d", allow_overruns=False)
    cron_job_id = cron_manager.CreateJob(cron_args=cron_args, token=self.token)

    self.RequestCronJobApproval(
        cron_job_id,
        reason=self.token.reason,
        approver=u"approver",
        requestor=self.token.username)

    args = user_plugin.ApiListCronJobApprovalsArgs()
    result = self.handler.Handle(args, token=self.token)

    self.assertLen(result.items, 1)


class ApiGetOwnGrrUserHandlerTest(api_test_lib.ApiCallHandlerTest):
  """Test for ApiGetUserSettingsHandler."""

  def setUp(self):
    super(ApiGetOwnGrrUserHandlerTest, self).setUp()
    self.handler = user_plugin.ApiGetOwnGrrUserHandler()

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
                      mode="ADVANCED",
                      canary_mode=True,
                  ))

    result = self.handler.Handle(
        None, token=access_control.ACLToken(username=u"foo"))
    self.assertEqual(result.settings.mode, "ADVANCED")
    self.assertEqual(result.settings.canary_mode, True)

  def testRendersTraitsPassedInConstructor(self):
    result = self.handler.Handle(
        None, token=access_control.ACLToken(username=u"foo"))
    self.assertFalse(result.interface_traits.create_hunt_action_enabled)

    handler = user_plugin.ApiGetOwnGrrUserHandler(
        interface_traits=user_plugin.ApiGrrUserInterfaceTraits(
            create_hunt_action_enabled=True))
    result = handler.Handle(
        None, token=access_control.ACLToken(username=u"foo"))
    self.assertTrue(result.interface_traits.create_hunt_action_enabled)


class ApiUpdateGrrUserHandlerTest(api_test_lib.ApiCallHandlerTest):
  """Tests for ApiUpdateUserSettingsHandler."""

  def setUp(self):
    super(ApiUpdateGrrUserHandlerTest, self).setUp()
    self.handler = user_plugin.ApiUpdateGrrUserHandler()

  def testRaisesIfUsernameSetInRequest(self):
    user = user_plugin.ApiGrrUser(username=u"foo")
    with self.assertRaises(ValueError):
      self.handler.Handle(user, token=access_control.ACLToken(username=u"foo"))

    user = user_plugin.ApiGrrUser(username=u"bar")
    with self.assertRaises(ValueError):
      self.handler.Handle(user, token=access_control.ACLToken(username=u"foo"))

  def testRaisesIfTraitsSetInRequest(self):
    user = user_plugin.ApiGrrUser(
        interface_traits=user_plugin.ApiGrrUserInterfaceTraits())
    with self.assertRaises(ValueError):
      self.handler.Handle(user, token=access_control.ACLToken(username=u"foo"))

  def testSetsSettingsForUserCorrespondingToToken(self):
    settings = aff4_users.GUISettings(mode="ADVANCED", canary_mode=True)
    user = user_plugin.ApiGrrUser(settings=settings)

    self.handler.Handle(user, token=access_control.ACLToken(username=u"foo"))

    # Check that settings for user "foo" were applied.
    fd = aff4.FACTORY.Open("aff4:/users/foo", token=self.token)
    self.assertEqual(fd.Get(fd.Schema.GUI_SETTINGS), settings)

    # Check that settings were applied in relational db.
    u = data_store.REL_DB.ReadGRRUser(u"foo")
    self.assertEqual(settings.mode, u.ui_mode)
    self.assertEqual(settings.canary_mode, u.canary_mode)


class ApiDeletePendingUserNotificationHandlerTest(
    api_test_lib.ApiCallHandlerTest):
  """Test for ApiDeletePendingUserNotificationHandler."""

  TIME_0 = rdfvalue.RDFDatetime(42 * rdfvalue.MICROSECONDS)
  TIME_1 = TIME_0 + rdfvalue.Duration("1d")
  TIME_2 = TIME_1 + rdfvalue.Duration("1d")

  def setUp(self):
    super(ApiDeletePendingUserNotificationHandlerTest, self).setUp()
    self.handler = user_plugin.ApiDeletePendingUserNotificationHandler()
    self.client_id = self.SetupClient(0)

    with test_lib.FakeTime(self.TIME_0):
      notification.Notify(
          self.token.username,
          rdf_objects.UserNotification.Type.TYPE_CLIENT_INTERROGATED,
          "<some message>",
          rdf_objects.ObjectReference(
              reference_type=rdf_objects.ObjectReference.Type.CLIENT,
              client=rdf_objects.ClientReference(
                  client_id=self.client_id.Basename())))

      notification.Notify(
          self.token.username,
          rdf_objects.UserNotification.Type.TYPE_CLIENT_INTERROGATED,
          "<some message with identical time>",
          rdf_objects.ObjectReference(
              reference_type=rdf_objects.ObjectReference.Type.CLIENT,
              client=rdf_objects.ClientReference(
                  client_id=self.client_id.Basename())))

    with test_lib.FakeTime(self.TIME_1):
      notification.Notify(
          self.token.username,
          rdf_objects.UserNotification.Type.TYPE_CLIENT_APPROVAL_GRANTED,
          "<some other message>",
          rdf_objects.ObjectReference(
              reference_type=rdf_objects.ObjectReference.Type.CLIENT,
              client=rdf_objects.ClientReference(
                  client_id=self.client_id.Basename())))

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
    self.assertLen(pending, 3)
    self.assertEmpty(shown)

    # Delete a pending notification.
    args = user_plugin.ApiDeletePendingUserNotificationArgs(
        timestamp=self.TIME_1)
    self.handler.Handle(args, token=self.token)

    # After the deletion, two notifications should be pending and one shown.
    (pending, shown) = self._GetNotifications()
    self.assertLen(pending, 2)
    self.assertLen(shown, 1)
    self.assertIn("<some other message>", shown[0].message)
    self.assertEqual(shown[0].timestamp, self.TIME_1)

  def testRaisesOnDeletingMultipleNotifications(self):
    # Check that there are three pending notifications and no shown ones yet.
    (pending, shown) = self._GetNotifications()
    self.assertLen(pending, 3)
    self.assertEmpty(shown)

    # Delete all pending notifications on TIME_0.
    args = user_plugin.ApiDeletePendingUserNotificationArgs(
        timestamp=self.TIME_0)
    with self.assertRaises(aff4_users.UniqueKeyError):
      self.handler.Handle(args, token=self.token)

    # Check that the notifications were not changed in the process.
    (pending, shown) = self._GetNotifications()
    self.assertLen(pending, 3)
    self.assertEmpty(shown)

  def testUnknownTimestampIsIgnored(self):
    # Check that there are three pending notifications and no shown ones yet.
    (pending, shown) = self._GetNotifications()
    self.assertLen(pending, 3)
    self.assertEmpty(shown)

    # A timestamp not matching any pending notifications does not change any of
    # the collections.
    args = user_plugin.ApiDeletePendingUserNotificationArgs(
        timestamp=self.TIME_2)
    self.handler.Handle(args, token=self.token)

    # We should still have the same number of pending and shown notifications.
    (pending, shown) = self._GetNotifications()
    self.assertLen(pending, 3)
    self.assertEmpty(shown)


@db_test_lib.DualDBTest
class ApiListApproverSuggestionsHandlerTest(acl_test_lib.AclTestMixin,
                                            api_test_lib.ApiCallHandlerTest):
  """Test for ApiListApproverSuggestionsHandler."""

  def setUp(self):
    super(ApiListApproverSuggestionsHandlerTest, self).setUp()
    self.handler = user_plugin.ApiListApproverSuggestionsHandler()
    self.CreateUser("sanchezmorty")
    self.CreateUser("sanchezrick")
    self.CreateUser("sanchezsummer")
    self.CreateUser("api_user_2")

  def _query(self, username):
    args = user_plugin.ApiListApproverSuggestionsArgs(username_query=username)
    return self.handler.Handle(args, token=self.token)

  def testListsSingleSuggestions(self):
    result = self._query("sanchezsu")
    self.assertLen(result.suggestions, 1)
    self.assertEqual(result.suggestions[0].username, "sanchezsummer")

  def testListsMultipleSuggestions(self):
    result = self._query("san")
    self.assertLen(result.suggestions, 3)
    self.assertEqual(result.suggestions[0].username, "sanchezmorty")
    self.assertEqual(result.suggestions[1].username, "sanchezrick")
    self.assertEqual(result.suggestions[2].username, "sanchezsummer")

  def testEmptyResponse(self):
    result = self._query("foo")
    self.assertEmpty(result.suggestions)

  def testExcludesCurrentUser(self):
    result = self._query("api")
    self.assertLen(result.suggestions, 1)
    self.assertEqual(result.suggestions[0].username, "api_user_2")


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
