#!/usr/bin/env python
"""This module contains tests for user API handlers."""

from typing import Optional
from unittest import mock

from absl import app

from google.protobuf import any_pb2
from grr_response_core import config
from grr_response_core.lib import rdfvalue
from grr_response_proto import flows_pb2
from grr_response_proto import objects_pb2
from grr_response_proto import user_pb2
from grr_response_proto.api import user_pb2 as api_user_pb2
from grr_response_server import access_control
from grr_response_server import cronjobs
from grr_response_server import data_store
from grr_response_server import email_alerts
from grr_response_server import flow
from grr_response_server import notification
from grr_response_server.databases import db_test_utils
from grr_response_server.flows import file
from grr_response_server.gui import access_controller
from grr_response_server.gui import api_call_context
from grr_response_server.gui import api_call_handler_base
from grr_response_server.gui import api_test_lib
from grr_response_server.gui.api_plugins import user as user_plugin
from grr_response_server.rdfvalues import cronjobs as rdf_cronjobs
from grr_response_server.rdfvalues import mig_objects
from grr.test_lib import acl_test_lib
from grr.test_lib import hunt_test_lib
from grr.test_lib import notification_test_lib
from grr.test_lib import test_lib


class ApiNotificationTest(
    acl_test_lib.AclTestMixin,
    notification_test_lib.NotificationTestMixin,
    api_test_lib.ApiCallHandlerTest,
):
  """Tests for ApiNotification class."""

  def setUp(self):
    super().setUp()
    self.client_id = self.SetupClient(0)

  def InitFromObj_(
      self,
      notification_type: objects_pb2.UserNotification.Type,
      reference: Optional[objects_pb2.ObjectReference] = None,
      message: Optional[str] = None,
  ) -> api_user_pb2.ApiNotification:
    self.CreateUser(self.context.username)
    notification.Notify(
        self.context.username, notification_type, message or "", reference
    )
    notifications = self.GetUserNotifications(self.context.username)
    notifications = [
        mig_objects.ToProtoUserNotification(n) for n in notifications
    ]

    # Treat the notification as an object coming from REL_DB.
    return user_plugin.InitApiNotificationFromUserNotification(notifications[0])

  def testDiscoveryNotificationIsParsedCorrectly(self):
    n = self.InitFromObj_(
        objects_pb2.UserNotification.Type.TYPE_CLIENT_INTERROGATED,
        objects_pb2.ObjectReference(
            reference_type=objects_pb2.ObjectReference.Type.CLIENT,
            client=objects_pb2.ClientReference(client_id=self.client_id),
        ),
    )

    self.assertEqual(
        n.reference.type, api_user_pb2.ApiNotificationReference.Type.CLIENT
    )
    self.assertEqual(n.reference.client.client_id, self.client_id)

  def testClientApprovalGrantedNotificationIsParsedCorrectly(self):
    n = self.InitFromObj_(
        objects_pb2.UserNotification.Type.TYPE_CLIENT_APPROVAL_GRANTED,
        objects_pb2.ObjectReference(
            reference_type=objects_pb2.ObjectReference.Type.CLIENT,
            client=objects_pb2.ClientReference(client_id=self.client_id),
        ),
    )

    self.assertEqual(
        n.reference.type, api_user_pb2.ApiNotificationReference.Type.CLIENT
    )
    self.assertEqual(n.reference.client.client_id, self.client_id)

  def testHuntNotificationIsParsedCorrectly(self):
    n = self.InitFromObj_(
        objects_pb2.UserNotification.Type.TYPE_HUNT_STOPPED,
        objects_pb2.ObjectReference(
            reference_type=objects_pb2.ObjectReference.Type.HUNT,
            hunt=objects_pb2.HuntReference(hunt_id="H:123456"),
        ),
    )

    self.assertEqual(
        n.reference.type, api_user_pb2.ApiNotificationReference.Type.HUNT
    )
    self.assertEqual(n.reference.hunt.hunt_id, "H:123456")

  def testCronNotificationIsParsedCorrectly(self):
    n = self.InitFromObj_(
        objects_pb2.UserNotification.Type.TYPE_CRON_JOB_APPROVAL_GRANTED,
        objects_pb2.ObjectReference(
            reference_type=objects_pb2.ObjectReference.Type.CRON_JOB,
            cron_job=objects_pb2.CronJobReference(cron_job_id="FooBar"),
        ),
    )

    self.assertEqual(
        n.reference.type, api_user_pb2.ApiNotificationReference.Type.CRON
    )
    self.assertEqual(n.reference.cron.cron_job_id, "FooBar")

  def testFlowSuccessNotificationIsParsedCorrectly(self):
    n = self.InitFromObj_(
        objects_pb2.UserNotification.Type.TYPE_FLOW_RUN_COMPLETED,
        objects_pb2.ObjectReference(
            reference_type=objects_pb2.ObjectReference.Type.FLOW,
            flow=objects_pb2.FlowReference(
                client_id=self.client_id, flow_id="F:123456"
            ),
        ),
    )

    self.assertEqual(
        n.reference.type, api_user_pb2.ApiNotificationReference.Type.FLOW
    )
    self.assertEqual(n.reference.flow.client_id, self.client_id)
    self.assertEqual(n.reference.flow.flow_id, "F:123456")

  def testFlowFailureNotificationIsParsedCorrectly(self):
    n = self.InitFromObj_(
        objects_pb2.UserNotification.Type.TYPE_FLOW_RUN_FAILED,
        objects_pb2.ObjectReference(
            reference_type=objects_pb2.ObjectReference.Type.FLOW,
            flow=objects_pb2.FlowReference(
                client_id=self.client_id, flow_id="F:123456"
            ),
        ),
    )

    self.assertEqual(
        n.reference.type, api_user_pb2.ApiNotificationReference.Type.FLOW
    )
    self.assertEqual(n.reference.flow.client_id, self.client_id)
    self.assertEqual(n.reference.flow.flow_id, "F:123456")

  def testVfsNotificationIsParsedCorrectly(self):
    n = self.InitFromObj_(
        objects_pb2.UserNotification.Type.TYPE_VFS_FILE_COLLECTED,
        objects_pb2.ObjectReference(
            reference_type=objects_pb2.ObjectReference.Type.VFS_FILE,
            vfs_file=objects_pb2.VfsFileReference(
                client_id=self.client_id,
                path_type=objects_pb2.PathInfo.PathType.OS,
                path_components=["foo", "bar"],
            ),
        ),
    )

    self.assertEqual(
        n.reference.type, api_user_pb2.ApiNotificationReference.Type.VFS
    )
    self.assertEqual(n.reference.vfs.client_id, self.client_id)
    self.assertEqual(n.reference.vfs.vfs_path, "fs/os/foo/bar")

  def testVfsNotificationWithInvalidReferenceIsParsedDefensively(self):
    n = self.InitFromObj_(
        objects_pb2.UserNotification.Type.TYPE_VFS_FILE_COLLECTED,
        objects_pb2.ObjectReference(
            reference_type=objects_pb2.ObjectReference.Type.VFS_FILE,
            vfs_file=objects_pb2.VfsFileReference(
                client_id=self.client_id,
                # UNSET path type is an invalid value here:
                # it make it impossible to find the file.
                path_type=objects_pb2.PathInfo.PathType.UNSET,
                path_components=["foo", "bar"],
            ),
        ),
    )

    self.assertEqual(
        n.reference.type, api_user_pb2.ApiNotificationReference.Type.UNSET
    )

  def testClientApprovalNotificationIsParsedCorrectly(self):
    n = self.InitFromObj_(
        objects_pb2.UserNotification.Type.TYPE_CLIENT_APPROVAL_REQUESTED,
        objects_pb2.ObjectReference(
            reference_type=objects_pb2.ObjectReference.Type.APPROVAL_REQUEST,
            approval_request=objects_pb2.ApprovalRequestReference(
                approval_type=objects_pb2.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CLIENT,
                approval_id="foo-bar",
                subject_id=self.client_id,
                requestor_username=self.context.username,
            ),
        ),
    )

    self.assertEqual(
        n.reference.type,
        api_user_pb2.ApiNotificationReference.Type.CLIENT_APPROVAL,
    )

    client_approval = n.reference.client_approval
    self.assertEqual(client_approval.client_id, self.client_id)
    self.assertEqual(client_approval.username, self.context.username)
    self.assertEqual(client_approval.approval_id, "foo-bar")

  def testHuntApprovalNotificationIsParsedCorrectly(self):
    n = self.InitFromObj_(
        objects_pb2.UserNotification.Type.TYPE_HUNT_APPROVAL_REQUESTED,
        objects_pb2.ObjectReference(
            reference_type=objects_pb2.ObjectReference.Type.APPROVAL_REQUEST,
            approval_request=objects_pb2.ApprovalRequestReference(
                approval_type=objects_pb2.ApprovalRequest.ApprovalType.APPROVAL_TYPE_HUNT,
                approval_id="foo-bar",
                subject_id="H:123456",
                requestor_username=self.context.username,
            ),
        ),
    )

    self.assertEqual(
        n.reference.type,
        api_user_pb2.ApiNotificationReference.Type.HUNT_APPROVAL,
    )
    self.assertEqual(n.reference.hunt_approval.hunt_id, "H:123456")
    self.assertEqual(n.reference.hunt_approval.username, self.context.username)
    self.assertEqual(n.reference.hunt_approval.approval_id, "foo-bar")

  def testCronJobApprovalNotificationIsParsedCorrectly(self):
    n = self.InitFromObj_(
        objects_pb2.UserNotification.Type.TYPE_CRON_JOB_APPROVAL_REQUESTED,
        objects_pb2.ObjectReference(
            reference_type=objects_pb2.ObjectReference.Type.APPROVAL_REQUEST,
            approval_request=objects_pb2.ApprovalRequestReference(
                approval_type=objects_pb2.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CRON_JOB,
                approval_id="foo-bar",
                subject_id="FooBar",
                requestor_username=self.context.username,
            ),
        ),
    )

    self.assertEqual(
        n.reference.type,
        api_user_pb2.ApiNotificationReference.Type.CRON_JOB_APPROVAL,
    )
    self.assertEqual(n.reference.cron_job_approval.cron_job_id, "FooBar")
    self.assertEqual(
        n.reference.cron_job_approval.username, self.context.username
    )
    self.assertEqual(n.reference.cron_job_approval.approval_id, "foo-bar")

  def testFileArchiveGenerationFailedNotificationIsParsedAsUnknownOrUnset(self):
    n = self.InitFromObj_(
        objects_pb2.UserNotification.Type.TYPE_FILE_ARCHIVE_GENERATION_FAILED,
        None,
        message="blah",
    )
    self.assertIn(
        n.reference.type,
        [
            api_user_pb2.ApiNotificationReference.Type.UNSET,
            api_user_pb2.ApiNotificationReference.Type.UNKNOWN,
        ],
    )
    self.assertEqual(n.message, "blah")

  def testVfsListDirectoryCompletedIsParsedCorrectly(self):
    n = self.InitFromObj_(
        objects_pb2.UserNotification.Type.TYPE_VFS_LIST_DIRECTORY_COMPLETED,
        objects_pb2.ObjectReference(
            reference_type=objects_pb2.ObjectReference.Type.VFS_FILE,
            vfs_file=objects_pb2.VfsFileReference(
                client_id=self.client_id,
                path_type=objects_pb2.PathInfo.PathType.OS,
                path_components=["foo", "bar"],
            ),
        ),
    )

    self.assertEqual(
        n.reference.type, api_user_pb2.ApiNotificationReference.Type.VFS
    )
    self.assertEqual(n.reference.vfs.client_id, self.client_id)
    self.assertEqual(n.reference.vfs.vfs_path, "fs/os/foo/bar")


class ApiCreateApprovalHandlerTestMixin(
    notification_test_lib.NotificationTestMixin, acl_test_lib.AclTestMixin
):
  """Base class for tests testing Create*ApprovalHandlers."""

  def SetUpApprovalTest(self):
    self.CreateUser("test")
    self.CreateUser("approver")

    self.handler = None
    self.args = None

  def ReadApproval(self, approval_id):
    raise NotImplementedError()

  def testCreatesAnApprovalWithGivenAttributes(self):
    approval_id = self.handler.Handle(self.args, context=self.context).id
    approval_obj = self.ReadApproval(approval_id)

    self.assertEqual(approval_obj.reason, "Running tests")
    self.assertEqual(approval_obj.approvers, [self.context.username])
    self.assertEqual(approval_obj.email_cc_addresses, ["test@example.com"])

  def testApproversFromArgsAreIgnored(self):
    # It shouldn't be possible to specify list of approvers when creating
    # an approval. List of approvers contains names of GRR users who
    # approved the approval.
    self.args.approval.approvers.extend([self.context.username, "approver"])

    approval_id = self.handler.Handle(self.args, context=self.context).id
    approval_obj = self.ReadApproval(approval_id)

    self.assertEqual(approval_obj.approvers, [self.context.username])

  def testRaisesOnEmptyReason(self):
    self.args.approval.reason = ""

    with self.assertRaises(ValueError):
      self.handler.Handle(self.args, context=self.context)

  def testNotifiesGrrUsers(self):
    self.handler.Handle(self.args, context=self.context)

    notifications = self.GetUserNotifications("approver")
    self.assertLen(notifications, 1)

  def testSendsEmailsToGrrUsersAndCcAddresses(self):
    with mock.patch.object(email_alerts.EMAIL_ALERTER, "SendEmail") as send_fn:
      self.handler.Handle(self.args, context=self.context)

    send_fn.assert_called_once()
    self.assertEqual(send_fn.call_args[1]["to_addresses"], "approver@localhost")
    self.assertEqual(
        send_fn.call_args[1]["from_address"],
        f"{self.context.username}@localhost",
    )
    self.assertEqual(send_fn.call_args[1]["cc_addresses"], "test@example.com")

    message = send_fn.call_args[1]["message"]
    self.assertIn(self.context.username, message)
    self.assertIn("Running tests", message)  # Request reason.


class ApiApprovalScheduledFlowsTest(
    acl_test_lib.AclTestMixin, api_test_lib.ApiCallHandlerTest
):

  def setUp(self):
    super().setUp()
    self.client_id = self.SetupClient(0)

  def testDoesNotStartScheduledFlowsIfGrantedApprovalIsNotValid(self):
    with mock.patch.object(flow, "StartScheduledFlows") as start_mock:
      with mock.patch.object(
          access_controller.ApprovalChecker,
          "CheckClientApprovals",
          side_effect=access_control.UnauthorizedAccess("foobazzle"),
      ):
        approval_id = self.RequestAndGrantClientApproval(
            self.client_id,
            reason="blah",
            approver="approver",
            requestor=self.context.username,
        )

        args = api_user_pb2.ApiGetClientApprovalArgs(
            client_id=self.client_id,
            approval_id=approval_id,
            username=self.context.username,
        )
        handler = user_plugin.ApiGetClientApprovalHandler()
        result = handler.Handle(args, context=self.context)

    self.assertFalse(result.is_valid)
    self.assertFalse(start_mock.called)

  def testStartsScheduledFlowsIfGrantedApprovalIsValid(self):
    with mock.patch.object(flow, "StartScheduledFlows") as start_mock:
      approval_id = self.RequestAndGrantClientApproval(
          self.client_id,
          reason="blah",
          approver="approver",
          requestor=self.context.username,
      )

    args = api_user_pb2.ApiGetClientApprovalArgs(
        client_id=self.client_id,
        approval_id=approval_id,
        username=self.context.username,
    )
    handler = user_plugin.ApiGetClientApprovalHandler()
    approval = handler.Handle(args, context=self.context)

    self.assertTrue(approval.is_valid)
    self.assertTrue(start_mock.called)
    start_mock.assert_called_with(
        client_id=self.client_id, creator=self.context.username
    )

  def testErrorDuringStartFlowDoesNotBubbleUpToApprovalApiCall(self):
    any_flow_args = any_pb2.Any()
    any_flow_args.Pack(flows_pb2.CollectFilesByKnownPathArgs(paths=["/foo"]))
    flow.ScheduleFlow(
        client_id=self.client_id,
        creator=self.context.username,
        flow_name=file.CollectFilesByKnownPath.__name__,
        flow_args=any_flow_args,
        runner_args=flows_pb2.FlowRunnerArgs(),
    )

    with mock.patch.object(
        flow, "StartFlow", side_effect=ValueError("foobazzle")
    ) as start_flow_mock:
      approval_id = self.RequestAndGrantClientApproval(
          self.client_id,
          reason="blah",
          approver="approver",
          requestor=self.context.username,
      )

    args = api_user_pb2.ApiGetClientApprovalArgs(
        client_id=self.client_id,
        approval_id=approval_id,
        username=self.context.username,
    )
    handler = user_plugin.ApiGetClientApprovalHandler()
    approval = handler.Handle(args, context=self.context)

    self.assertTrue(approval.is_valid)
    self.assertTrue(start_flow_mock.called)


class ApiGetClientApprovalHandlerTest(
    acl_test_lib.AclTestMixin, api_test_lib.ApiCallHandlerTest
):
  """Test for ApiGetClientApprovalHandler."""

  def setUp(self):
    super().setUp()
    self.client_id = self.SetupClient(0)
    self.handler = user_plugin.ApiGetClientApprovalHandler()

  def testRendersRequestedClientApproval(self):
    approval_id = self.RequestClientApproval(
        self.client_id,
        requestor=self.context.username,
        reason="blah",
        approver="approver",
        email_cc_address="test@example.com",
    )

    args = api_user_pb2.ApiGetClientApprovalArgs(
        client_id=self.client_id,
        approval_id=approval_id,
        username=self.context.username,
    )
    result = self.handler.Handle(args, context=self.context)

    self.assertEqual(result.subject.client_id, self.client_id)
    self.assertEqual(result.reason, "blah")
    self.assertEqual(result.is_valid, False)
    self.assertEqual(
        result.is_valid_message,
        "Need at least 1 additional approver for access.",
    )

    self.assertEqual(result.notified_users, ["approver"])
    self.assertEqual(result.email_cc_addresses, ["test@example.com"])

    # Every approval is self-approved by default.
    self.assertEqual(result.approvers, [self.context.username])

  def testIncludesApproversInResultWhenApprovalIsGranted(self):
    approval_id = self.RequestAndGrantClientApproval(
        self.client_id,
        reason="blah",
        approver="approver",
        requestor=self.context.username,
    )

    args = api_user_pb2.ApiGetClientApprovalArgs(
        client_id=self.client_id,
        approval_id=approval_id,
        username=self.context.username,
    )
    result = self.handler.Handle(args, context=self.context)

    self.assertTrue(result.is_valid)
    self.assertCountEqual(result.approvers, [self.context.username, "approver"])

  def testRaisesWhenApprovalIsNotFound(self):
    args = api_user_pb2.ApiGetClientApprovalArgs(
        client_id=self.client_id,
        approval_id="approval:112233",
        username=self.context.username,
    )

    with self.assertRaises(api_call_handler_base.ResourceNotFoundError):
      self.handler.Handle(args, context=self.context)


class ApiCreateClientApprovalHandlerTest(
    api_test_lib.ApiCallHandlerTest, ApiCreateApprovalHandlerTestMixin
):
  """Test for ApiCreateClientApprovalHandler."""

  def ReadApproval(self, approval_id):
    approvals = self.ListClientApprovals(requestor=self.context.username)
    self.assertLen(approvals, 1)
    self.assertEqual(approvals[0].id, approval_id)
    return approvals[0]

  def setUp(self):
    super().setUp()

    self.SetUpApprovalTest()

    self.client_id = self.SetupClient(0)

    self.handler = user_plugin.ApiCreateClientApprovalHandler()

    self.args = api_user_pb2.ApiCreateClientApprovalArgs(
        client_id=self.client_id
    )
    self.args.approval.reason = "Running tests"
    self.args.approval.notified_users.append("approver")
    self.args.approval.email_cc_addresses.append("test@example.com")

  def testSendsEmailWithApprovalInformation(self):
    with mock.patch.object(email_alerts.EMAIL_ALERTER, "SendEmail") as send_fn:
      approval_id = self.handler.Handle(self.args, self.context).id

    send_fn.assert_called_once()
    message = send_fn.call_args[1]["message"]
    self.assertIn(
        (
            f"http://localhost:8000/v2/clients/{self.client_id}/approvals/"
            f"{approval_id}/users/{self.context.username}"
        ),
        message,
    )

    self.assertIn(self.context.username, message)
    self.assertIn("Running tests", message)  # Request reason.
    self.assertIn(self.client_id, message)

  def testDefaultExpiration(self):
    """Tests that when no expiration is specified the default is used."""
    with (
        mock.patch.object(email_alerts.EMAIL_ALERTER, "SendEmail"),
        mock.patch.object(rdfvalue.RDFDatetime, "Now") as mock_now,
    ):
      oneday_s = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(24 * 60 * 60)
      mock_now.return_value = oneday_s  # 'Now' is 1 day past epoch

      approval = self.handler.Handle(self.args, self.context)

      # 'Now' is one day past epoch, plus the default expiration
      twentyninedays_us = (
          config.CONFIG["ACL.token_expiry"] * 1000000
      ) + oneday_s.AsMicrosecondsSinceEpoch()

    self.assertEqual(approval.expiration_time_us, int(twentyninedays_us))

  def testCorrectNonDefaultExpiration(self):
    """Tests that a custom expiration is correctly applied."""
    with (
        mock.patch.object(email_alerts.EMAIL_ALERTER, "SendEmail"),
        mock.patch.object(rdfvalue.RDFDatetime, "Now") as mock_now,
    ):
      mock_now.return_value = (  # 'Now' is 1 day past epoch
          rdfvalue.RDFDatetime.FromSecondsSinceEpoch(24 * 60 * 60)
      )
      onetwentydays_us = 120 * 24 * 60 * 60 * 1000000

      self.args.approval.expiration_time_us = int(
          rdfvalue.RDFDatetime.FromMicrosecondsSinceEpoch(onetwentydays_us)
      )
      approval = self.handler.Handle(self.args, self.context)

    self.assertEqual(approval.expiration_time_us, onetwentydays_us)

  def testNonDefaultExpirationInPast(self):
    """Tests that a custom expiration in the past raises an error."""
    with (
        mock.patch.object(email_alerts.EMAIL_ALERTER, "SendEmail"),
        mock.patch.object(rdfvalue.RDFDatetime, "Now") as mock_now,
    ):
      mock_now.return_value = (  # 'Now' is 1 day past epoch
          rdfvalue.RDFDatetime.FromSecondsSinceEpoch(24 * 60 * 60)
      )

      onehour_us = 60 * 60 * 1000000
      self.args.approval.expiration_time_us = onehour_us

      with self.assertRaisesRegex(
          ValueError,
          "Requested expiration time 1970-01-01 01:00:00 is in the past.",
      ):
        self.handler.Handle(self.args, self.context)

  def testNonDefaultExpirationTooLong(self):
    """Tests that a custom expiration too far in the future raises an error."""
    with (
        mock.patch.object(email_alerts.EMAIL_ALERTER, "SendEmail"),
        mock.patch.object(rdfvalue.RDFDatetime, "Now") as mock_now,
    ):
      mock_now.return_value = (  # 'Now' is 1 day past epoch
          rdfvalue.RDFDatetime.FromSecondsSinceEpoch(24 * 60 * 60)
      )

      fourhundreddays_us = 400 * 24 * 60 * 60 * 1000000
      self.args.approval.expiration_time_us = fourhundreddays_us

      with self.assertRaisesRegex(
          ValueError,
          "Requested expiration time 1971-02-05 00:00:00 is too far in the "
          "future.",
      ):
        self.handler.Handle(self.args, self.context)


class ApiListClientApprovalsHandlerTest(
    api_test_lib.ApiCallHandlerTest, acl_test_lib.AclTestMixin
):
  """Test for ApiListApprovalsHandler."""

  CLIENT_COUNT = 5

  def setUp(self):
    super().setUp()
    self.handler = user_plugin.ApiListClientApprovalsHandler()
    self.client_ids = self.SetupClients(self.CLIENT_COUNT)

  def _RequestClientApprovals(self):
    approval_ids = []
    for client_id in self.client_ids:
      approval_ids.append(self.RequestClientApproval(client_id))
    return approval_ids

  def testRendersRequestedClientApprovals(self):
    self._RequestClientApprovals()

    args = api_user_pb2.ApiListClientApprovalsArgs()
    result = self.handler.Handle(args, context=self.context)

    # All approvals should be returned.
    self.assertLen(result.items, self.CLIENT_COUNT)

  def testFiltersApprovalsByClientId(self):
    client_id = self.client_ids[0]

    self._RequestClientApprovals()

    # Get approvals for a specific client. There should be exactly one.
    args = api_user_pb2.ApiListClientApprovalsArgs(client_id=client_id)
    result = self.handler.Handle(args, context=self.context)

    self.assertLen(result.items, 1)
    self.assertEqual(result.items[0].subject.client_id, client_id)

  def testFiltersApprovalsByInvalidState(self):
    approval_ids = self._RequestClientApprovals()

    # We only requested approvals so far, so all of them should be invalid.
    args = api_user_pb2.ApiListClientApprovalsArgs(
        state=api_user_pb2.ApiListClientApprovalsArgs.State.INVALID
    )
    result = self.handler.Handle(args, context=self.context)

    self.assertLen(result.items, self.CLIENT_COUNT)

    # Grant access to one client. Now all but one should be invalid.
    self.GrantClientApproval(
        self.client_ids[0],
        requestor=self.context.username,
        approval_id=approval_ids[0],
    )
    result = self.handler.Handle(args, context=self.context)
    self.assertLen(result.items, self.CLIENT_COUNT - 1)

  def testFiltersApprovalsByValidState(self):
    approval_ids = self._RequestClientApprovals()

    # We only requested approvals so far, so none of them is valid.
    args = api_user_pb2.ApiListClientApprovalsArgs(
        state=api_user_pb2.ApiListClientApprovalsArgs.State.VALID
    )
    result = self.handler.Handle(args, context=self.context)

    # We do not have any approved approvals yet.
    self.assertEmpty(result.items)

    # Grant access to one client. Now exactly one approval should be valid.
    self.GrantClientApproval(
        self.client_ids[0],
        requestor=self.context.username,
        approval_id=approval_ids[0],
    )
    result = self.handler.Handle(args, context=self.context)
    self.assertLen(result.items, 1)
    self.assertEqual(result.items[0].subject.client_id, self.client_ids[0])

  def testFiltersApprovalsByClientIdAndState(self):
    client_id = self.client_ids[0]

    approval_ids = self._RequestClientApprovals()

    # Grant approval to a certain client.
    self.GrantClientApproval(
        client_id, requestor=self.context.username, approval_id=approval_ids[0]
    )

    args = api_user_pb2.ApiListClientApprovalsArgs(
        client_id=client_id,
        state=api_user_pb2.ApiListClientApprovalsArgs.State.VALID,
    )
    result = self.handler.Handle(args, context=self.context)

    # We have a valid approval for the requested client.
    self.assertLen(result.items, 1)

    args.state = api_user_pb2.ApiListClientApprovalsArgs.State.INVALID
    result = self.handler.Handle(args, context=self.context)

    # However, we do not have any invalid approvals for the client.
    self.assertEmpty(result.items)

  def testFiltersApprovalsByStateWithOffsetAndCount(self):
    approval_ids = self._RequestClientApprovals()

    # Grant approval to certain clients.
    self.GrantClientApproval(
        self.client_ids[0],
        requestor=self.context.username,
        approval_id=approval_ids[0],
    )
    self.GrantClientApproval(
        self.client_ids[1],
        requestor=self.context.username,
        approval_id=approval_ids[1],
    )
    self.GrantClientApproval(
        self.client_ids[2],
        requestor=self.context.username,
        approval_id=approval_ids[2],
    )

    args = api_user_pb2.ApiListClientApprovalsArgs(
        state=api_user_pb2.ApiListClientApprovalsArgs.State.VALID,
        offset=1,
        count=1,
    )
    result = self.handler.Handle(args, context=self.context)

    self.assertLen(result.items, 1)
    self.assertEqual(result.items[0].subject.client_id, self.client_ids[1])

  def testFilterConsidersOffsetAndCount(self):
    client_id = self.client_ids[0]

    # Create five approval requests without granting them.
    for i in range(10):
      with test_lib.FakeTime(42 + i):
        self.RequestClientApproval(client_id, reason="Request reason %d" % i)

    args = api_user_pb2.ApiListClientApprovalsArgs(
        client_id=client_id, offset=0, count=5
    )
    result = self.handler.Handle(args, context=self.context)

    # Approvals are returned newest to oldest, so the first five approvals
    # have reason 9 to 5.
    self.assertLen(result.items, 5)
    for item, i in zip(result.items, reversed(range(6, 10))):
      self.assertEqual(item.reason, "Request reason %d" % i)

    # When no count is specified, take all items from offset to the end.
    args = api_user_pb2.ApiListClientApprovalsArgs(
        client_id=client_id, offset=7
    )
    result = self.handler.Handle(args, context=self.context)

    self.assertLen(result.items, 3)
    for item, i in zip(result.items, reversed(range(0, 3))):
      self.assertEqual(item.reason, "Request reason %d" % i)


class ApiCreateHuntApprovalHandlerTest(
    ApiCreateApprovalHandlerTestMixin,
    hunt_test_lib.StandardHuntTestMixin,
    api_test_lib.ApiCallHandlerTest,
):
  """Test for ApiCreateHuntApprovalHandler."""

  def ReadApproval(self, approval_id):
    approvals = self.ListHuntApprovals(requestor=self.context.username)
    self.assertLen(approvals, 1)
    self.assertEqual(approvals[0].id, approval_id)
    return approvals[0]

  def setUp(self):
    super().setUp()

    self.SetUpApprovalTest()

    hunt_id = self.StartHunt(description="foo")

    self.handler = user_plugin.ApiCreateHuntApprovalHandler()

    self.args = api_user_pb2.ApiCreateHuntApprovalArgs(hunt_id=hunt_id)
    self.args.approval.reason = "Running tests"
    self.args.approval.notified_users.append("approver")
    self.args.approval.email_cc_addresses.append("test@example.com")


class ApiListHuntApprovalsHandlerTest(
    hunt_test_lib.StandardHuntTestMixin, api_test_lib.ApiCallHandlerTest
):
  """Test for ApiListHuntApprovalsHandler."""

  def setUp(self):
    super().setUp()
    self.handler = user_plugin.ApiListHuntApprovalsHandler()

  def testRendersRequestedHuntAppoval(self):
    hunt_id = self.StartHunt()

    self.RequestHuntApproval(
        hunt_id,
        reason="Running tests",
        approver="approver",
        requestor=self.context.username,
    )

    args = api_user_pb2.ApiListHuntApprovalsArgs()
    result = self.handler.Handle(args, context=self.context)

    self.assertLen(result.items, 1)


class ApiCreateCronJobApprovalHandlerTest(
    ApiCreateApprovalHandlerTestMixin,
    api_test_lib.ApiCallHandlerTest,
):
  """Test for ApiCreateCronJobApprovalHandler."""

  def ReadApproval(self, approval_id):
    approvals = self.ListCronJobApprovals(requestor=self.context.username)
    self.assertLen(approvals, 1)
    self.assertEqual(approvals[0].id, approval_id)
    return approvals[0]

  def setUp(self):
    super().setUp()

    self.SetUpApprovalTest()

    cron_manager = cronjobs.CronManager()
    cron_args = rdf_cronjobs.CreateCronJobArgs(
        frequency="1d",
        allow_overruns=False,
        flow_name=file.CollectFilesByKnownPath.__name__,
    )
    cron_id = cron_manager.CreateJob(cron_args=cron_args)

    self.handler = user_plugin.ApiCreateCronJobApprovalHandler()

    self.args = api_user_pb2.ApiCreateCronJobApprovalArgs(cron_job_id=cron_id)
    self.args.approval.reason = "Running tests"
    self.args.approval.notified_users.append("approver")
    self.args.approval.email_cc_addresses.append("test@example.com")


class ApiListCronJobApprovalsHandlerTest(
    acl_test_lib.AclTestMixin, api_test_lib.ApiCallHandlerTest
):
  """Test for ApiListCronJobApprovalsHandler."""

  def setUp(self):
    super().setUp()
    self.handler = user_plugin.ApiListCronJobApprovalsHandler()

  def testRendersRequestedCronJobApproval(self):
    cron_manager = cronjobs.CronManager()
    cron_args = rdf_cronjobs.CreateCronJobArgs(
        frequency="1d",
        allow_overruns=False,
        flow_name=file.CollectFilesByKnownPath.__name__,
    )
    cron_job_id = cron_manager.CreateJob(cron_args=cron_args)

    self.RequestCronJobApproval(
        cron_job_id,
        reason="Running tests",
        approver="approver",
        requestor=self.context.username,
    )

    args = api_user_pb2.ApiListCronJobApprovalsArgs()
    result = self.handler.Handle(args, context=self.context)

    self.assertLen(result.items, 1)


class ApiGetOwnGrrUserHandlerTest(api_test_lib.ApiCallHandlerTest):
  """Test for ApiGetUserSettingsHandler."""

  def setUp(self):
    super().setUp()
    data_store.REL_DB.WriteGRRUser("foo")
    self.handler = user_plugin.ApiGetOwnGrrUserHandler()

  def testRendersSettingsForUserCorrespondingToContext(self):
    data_store.REL_DB.WriteGRRUser(
        "foo", ui_mode=user_pb2.GUISettings.UIMode.ADVANCED, canary_mode=True
    )

    result = self.handler.Handle(
        None, context=api_call_context.ApiCallContext(username="foo")
    )
    self.assertEqual(result.settings.mode, user_pb2.GUISettings.UIMode.ADVANCED)
    self.assertEqual(result.settings.canary_mode, True)


class ApiUpdateGrrUserHandlerTest(api_test_lib.ApiCallHandlerTest):
  """Tests for ApiUpdateUserSettingsHandler."""

  def setUp(self):
    super().setUp()
    self.handler = user_plugin.ApiUpdateGrrUserHandler()

  def testRaisesIfUsernameSetInRequest(self):
    user = api_user_pb2.ApiGrrUser(username="foo")
    with self.assertRaises(ValueError):
      self.handler.Handle(
          user, context=api_call_context.ApiCallContext(username="foo")
      )

    user = api_user_pb2.ApiGrrUser(username="bar")
    with self.assertRaises(ValueError):
      self.handler.Handle(
          user, context=api_call_context.ApiCallContext(username="foo")
      )

  def testSetsSettingsForUserCorrespondingToToken(self):
    settings = user_pb2.GUISettings(
        mode=user_pb2.GUISettings.UIMode.ADVANCED, canary_mode=True
    )
    user = api_user_pb2.ApiGrrUser(settings=settings)

    self.handler.Handle(
        user, context=api_call_context.ApiCallContext(username="foo")
    )

    user = data_store.REL_DB.ReadGRRUser("foo")
    self.assertEqual(settings.mode, user.ui_mode)
    self.assertEqual(settings.canary_mode, user.canary_mode)


class ApiDeletePendingUserNotificationHandlerTest(
    api_test_lib.ApiCallHandlerTest
):
  """Test for ApiDeletePendingUserNotificationHandler."""

  TIME_0 = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(42)
  TIME_1 = TIME_0 + rdfvalue.Duration.From(1, rdfvalue.DAYS)
  TIME_2 = TIME_1 + rdfvalue.Duration.From(1, rdfvalue.DAYS)

  def setUp(self):
    super().setUp()
    self.handler = user_plugin.ApiDeletePendingUserNotificationHandler()
    self.client_id = self.SetupClient(0)

    with test_lib.FakeTime(self.TIME_0):
      notification.Notify(
          self.context.username,
          objects_pb2.UserNotification.Type.TYPE_CLIENT_INTERROGATED,
          "<some message>",
          objects_pb2.ObjectReference(
              reference_type=objects_pb2.ObjectReference.Type.CLIENT,
              client=objects_pb2.ClientReference(client_id=self.client_id),
          ),
      )

      notification.Notify(
          self.context.username,
          objects_pb2.UserNotification.Type.TYPE_CLIENT_INTERROGATED,
          "<some message with identical time>",
          objects_pb2.ObjectReference(
              reference_type=objects_pb2.ObjectReference.Type.CLIENT,
              client=objects_pb2.ClientReference(client_id=self.client_id),
          ),
      )

    with test_lib.FakeTime(self.TIME_1):
      notification.Notify(
          self.context.username,
          objects_pb2.UserNotification.Type.TYPE_CLIENT_APPROVAL_GRANTED,
          "<some other message>",
          objects_pb2.ObjectReference(
              reference_type=objects_pb2.ObjectReference.Type.CLIENT,
              client=objects_pb2.ClientReference(client_id=self.client_id),
          ),
      )

  def _GetNotifications(
      self,
  ) -> tuple[
      list[objects_pb2.UserNotification], list[objects_pb2.UserNotification]
  ]:
    pending = data_store.REL_DB.ReadUserNotifications(
        self.context.username,
        state=objects_pb2.UserNotification.State.STATE_PENDING,
    )
    shown = data_store.REL_DB.ReadUserNotifications(
        self.context.username,
        state=objects_pb2.UserNotification.State.STATE_NOT_PENDING,
    )
    return pending, shown

  def testDeletesFromPendingAndAddsToShown(self):
    # Check that there are three pending notifications and no shown ones yet.
    (pending, shown) = self._GetNotifications()
    self.assertLen(pending, 3)
    self.assertEmpty(shown)

    # Delete a pending notification.
    args = api_user_pb2.ApiDeletePendingUserNotificationArgs(
        timestamp=int(self.TIME_1)
    )
    self.handler.Handle(args, context=self.context)

    # After the deletion, two notifications should be pending and one shown.
    (pending, shown) = self._GetNotifications()
    self.assertLen(pending, 2)
    self.assertLen(shown, 1)
    self.assertIn("<some other message>", shown[0].message)
    self.assertEqual(shown[0].timestamp, int(self.TIME_1))

  def testUnknownTimestampIsIgnored(self):
    # Check that there are three pending notifications and no shown ones yet.
    (pending, shown) = self._GetNotifications()
    self.assertLen(pending, 3)
    self.assertEmpty(shown)

    # A timestamp not matching any pending notifications does not change any of
    # the collections.
    args = api_user_pb2.ApiDeletePendingUserNotificationArgs(
        timestamp=int(self.TIME_2)
    )
    self.handler.Handle(args, context=self.context)

    # We should still have the same number of pending and shown notifications.
    (pending, shown) = self._GetNotifications()
    self.assertLen(pending, 3)
    self.assertEmpty(shown)


class ApiListApproverSuggestionsHandlerTest(
    acl_test_lib.AclTestMixin, api_test_lib.ApiCallHandlerTest
):
  """Test for ApiListApproverSuggestionsHandler."""

  def setUp(self):
    super().setUp()
    self.handler = user_plugin.ApiListApproverSuggestionsHandler()
    self.CreateUser("sanchezmorty")
    self.CreateUser("sanchezrick")
    self.CreateUser("sanchezsummer")
    self.CreateUser("api_user_2")

  def _query(self, username):
    args = api_user_pb2.ApiListApproverSuggestionsArgs(username_query=username)
    return self.handler.Handle(args, context=self.context)

  def testListsSingleSuggestions(self):
    result = self._query("sanchezs")
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

  def testExcludesSystemUsers(self):
    non_system_username = db_test_utils.InitializeUser(data_store.REL_DB)
    db_test_utils.InitializeUser(data_store.REL_DB, "GRRWorker")
    db_test_utils.InitializeUser(data_store.REL_DB, "GRRCron")

    result = self._query("")
    result_usernames = [_.username for _ in result.suggestions]

    self.assertIn(non_system_username, result_usernames)
    self.assertNotIn("GRRWorker", result_usernames)
    self.assertNotIn("GRRCron", result_usernames)

  def testSuggestsMostRequestedUsers(self):
    client_id = self.SetupClient(0)
    self.RequestClientApproval(client_id, approver="sanchezmorty")
    self.RequestClientApproval(client_id, approver="sanchezsummer")
    self.RequestClientApproval(client_id, approver="sanchezsummer")

    result = self._query("")

    self.assertLen(result.suggestions, 2)
    self.assertEqual(result.suggestions[0].username, "sanchezsummer")
    self.assertEqual(result.suggestions[1].username, "sanchezmorty")

  def testSuggestsAllOtherUsersAsFallback(self):
    result = self._query("")

    self.assertLen(result.suggestions, 4)
    self.assertEqual(result.suggestions[0].username, "api_user_2")
    self.assertEqual(result.suggestions[1].username, "sanchezmorty")
    self.assertEqual(result.suggestions[2].username, "sanchezrick")
    self.assertEqual(result.suggestions[3].username, "sanchezsummer")


class ApiGrantClientApprovalHandlerTest(
    api_test_lib.ApiCallHandlerTest, acl_test_lib.AclTestMixin
):
  """Test for ApiGrantClientApprovalHandler."""

  def setUp(self):
    super().setUp()

    self.CreateUser("requestuser")
    self.client_id = self.SetupClient(0)
    self.handler = user_plugin.ApiGrantClientApprovalHandler()

  def testSendsEmailWithApprovalGrantInformation(self):
    approval_id = self.RequestClientApproval(
        self.client_id, reason="requestreason", requestor="requestuser"
    )

    with mock.patch.object(email_alerts.EMAIL_ALERTER, "SendEmail") as send_fn:
      self.handler.Handle(
          api_user_pb2.ApiGrantClientApprovalArgs(
              client_id=self.client_id,
              approval_id=approval_id,
              username="requestuser",
          ),
          self.context,
      )

    send_fn.assert_called_once()
    message = send_fn.call_args[1]["message"]
    self.assertIn(
        f'href="http://localhost:8000/v2/clients/{self.client_id}"', message
    )
    self.assertIn(self.context.username, message)
    self.assertIn("requestreason", message)
    self.assertIn(self.client_id, message)


class ApiGrantHuntApprovalHandlerTest(
    api_test_lib.ApiCallHandlerTest,
    hunt_test_lib.StandardHuntTestMixin,
    acl_test_lib.AclTestMixin,
):
  """Test for ApiGrantHuntApprovalHandler."""

  def setUp(self):
    super().setUp()

    self.CreateUser("requestuser")
    self.hunt_id = self.CreateHunt(creator="requestuser")
    self.handler = user_plugin.ApiGrantHuntApprovalHandler()

  def testSendsEmailWithApprovalGrantInformation(self):
    approval_id = self.RequestHuntApproval(
        self.hunt_id, reason="requestreason", requestor="requestuser"
    )

    with mock.patch.object(email_alerts.EMAIL_ALERTER, "SendEmail") as send_fn:
      self.handler.Handle(
          api_user_pb2.ApiGrantHuntApprovalArgs(
              hunt_id=self.hunt_id,
              approval_id=approval_id,
              username="requestuser",
          ),
          self.context,
      )

    send_fn.assert_called_once()
    message = send_fn.call_args[1]["message"]
    self.assertIn(
        f'href="http://localhost:8000/v2/fleet-collections/{self.hunt_id}"',
        message,
    )
    self.assertIn(self.context.username, message)
    self.assertIn("requestreason", message)
    self.assertIn(self.hunt_id, message)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
