#!/usr/bin/env python
"""This module contains regression tests for user API handlers."""

from grr.gui import api_regression_test_lib
from grr.gui.api_plugins import user as user_plugin

from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib.rdfvalues import hunts as rdf_hunts
from grr.lib.rdfvalues import objects as rdf_objects
from grr.server import access_control
from grr.server import aff4
from grr.server import data_store
from grr.server import flow

from grr.server.aff4_objects import cronjobs as aff4_cronjobs
from grr.server.aff4_objects import security
from grr.server.aff4_objects import users as aff4_users
from grr.server.flows.general import discovery
from grr.server.hunts import implementation
from grr.server.hunts import standard

from grr.server.hunts import standard_test
from grr.test_lib import acl_test_lib
from grr.test_lib import test_lib


class ApiGetClientApprovalHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest, acl_test_lib.AclTestMixin):
  """Regression test for ApiGetClientApprovalHandler."""

  api_method = "GetClientApproval"
  handler = user_plugin.ApiGetClientApprovalHandler

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
      approval_urn = security.ClientApprovalRequestor(
          reason="foo",
          subject_urn=clients[0],
          approver="approver",
          token=self.token).Request()
      approval1_id = approval_urn.Basename()

    with test_lib.FakeTime(45):
      approval_urn = security.ClientApprovalRequestor(
          reason="bar",
          subject_urn=clients[1],
          approver="approver",
          token=self.token).Request()
      approval2_id = approval_urn.Basename()

    with test_lib.FakeTime(84):
      approver_token = access_control.ACLToken(username="approver")
      security.ClientApprovalGrantor(
          reason="bar",
          delegate=self.token.username,
          subject_urn=clients[1],
          token=approver_token).Grant()

    with test_lib.FakeTime(126):
      self.Check(
          "GetClientApproval",
          args=user_plugin.ApiGetClientApprovalArgs(
              client_id=clients[0].Basename(),
              approval_id=approval1_id,
              username=self.token.username),
          replace={
              approval1_id: "approval:111111"
          })
      self.Check(
          "GetClientApproval",
          args=user_plugin.ApiGetClientApprovalArgs(
              client_id=clients[1].Basename(),
              approval_id=approval2_id,
              username=self.token.username),
          replace={
              approval2_id: "approval:222222"
          })


class ApiGrantClientApprovalHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest, acl_test_lib.AclTestMixin):
  """Regression test for ApiGrantClientApprovalHandler."""

  api_method = "GrantClientApproval"
  handler = user_plugin.ApiGrantClientApprovalHandler

  def Run(self):
    with test_lib.FakeTime(42):
      self.CreateAdminUser("requestor")

      client_id = self.SetupClient(0)
      # Delete the certificate as it's being regenerated every time the
      # client is created.
      with aff4.FACTORY.Open(
          client_id, mode="rw", token=self.token) as grr_client:
        grr_client.DeleteAttribute(grr_client.Schema.CERT)

    with test_lib.FakeTime(44):
      requestor_token = access_control.ACLToken(username="requestor")
      approval_urn = security.ClientApprovalRequestor(
          reason="foo",
          subject_urn=client_id,
          approver=self.token.username,
          token=requestor_token).Request()
      approval_id = approval_urn.Basename()

    with test_lib.FakeTime(126):
      self.Check(
          "GrantClientApproval",
          args=user_plugin.ApiGrantClientApprovalArgs(
              client_id=client_id.Basename(),
              approval_id=approval_id,
              username="requestor"),
          replace={
              approval_id: "approval:111111"
          })


class ApiCreateClientApprovalHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest, acl_test_lib.AclTestMixin):
  """Regression test for ApiCreateClientApprovalHandler."""

  api_method = "CreateClientApproval"
  handler = user_plugin.ApiCreateClientApprovalHandler

  def Run(self):
    with test_lib.FakeTime(42):
      self.CreateUser("approver")

      client_id = self.SetupClient(0)

      # Delete the certificate as it's being regenerated every time the
      # client is created.
      with aff4.FACTORY.Open(
          client_id, mode="rw", token=self.token) as grr_client:
        grr_client.DeleteAttribute(grr_client.Schema.CERT)

    def ReplaceApprovalId():
      approvals = list(
          aff4.FACTORY.ListChildren(
              aff4.ROOT_URN.Add("ACL").Add(client_id.Basename()).Add(
                  self.token.username)))

      return {approvals[0].Basename(): "approval:112233"}

    with test_lib.FakeTime(126):
      self.Check(
          "CreateClientApproval",
          args=user_plugin.ApiCreateClientApprovalArgs(
              client_id=client_id.Basename(),
              approval=user_plugin.ApiClientApproval(
                  reason="really important reason!",
                  notified_users=["approver1", "approver2"],
                  email_cc_addresses=["test@example.com"])),
          replace=ReplaceApprovalId)


class ApiListClientApprovalsHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest, acl_test_lib.AclTestMixin):
  """Regression test for ApiListClientApprovalsHandlerTest."""

  api_method = "ListClientApprovals"
  handler = user_plugin.ApiListClientApprovalsHandler

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
      approval_urn = security.ClientApprovalRequestor(
          reason=self.token.reason,
          subject_urn=clients[0],
          approver="approver",
          token=self.token).Request()
      approval1_id = approval_urn.Basename()

    with test_lib.FakeTime(45):
      approval_urn = security.ClientApprovalRequestor(
          reason=self.token.reason,
          subject_urn=clients[1],
          approver="approver",
          token=self.token).Request()
      approval2_id = approval_urn.Basename()

    with test_lib.FakeTime(84):
      approver_token = access_control.ACLToken(username="approver")
      security.ClientApprovalGrantor(
          reason=self.token.reason,
          delegate=self.token.username,
          subject_urn=clients[1],
          token=approver_token).Grant()

    with test_lib.FakeTime(126):
      self.Check(
          "ListClientApprovals",
          args=user_plugin.ApiListClientApprovalsArgs(),
          replace={
              approval1_id: "approval:111111",
              approval2_id: "approval:222222"
          })
      self.Check(
          "ListClientApprovals",
          args=user_plugin.ApiListClientApprovalsArgs(
              client_id=clients[0].Basename()),
          replace={
              approval1_id: "approval:111111",
              approval2_id: "approval:222222"
          })


class ApiGetHuntApprovalHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest,
    standard_test.StandardHuntTestMixin, acl_test_lib.AclTestMixin):
  """Regression test for ApiGetHuntApprovalHandler."""

  api_method = "GetHuntApproval"
  handler = user_plugin.ApiGetHuntApprovalHandler

  def _RunTestForNormalApprovals(self):
    with test_lib.FakeTime(42):
      self.CreateAdminUser("approver")

      with self.CreateHunt(description="hunt1") as hunt_obj:
        hunt1_urn = hunt_obj.urn
        hunt1_id = hunt1_urn.Basename()

      with self.CreateHunt(description="hunt2") as hunt_obj:
        hunt2_urn = hunt_obj.urn
        hunt2_id = hunt2_urn.Basename()

    with test_lib.FakeTime(44):
      approval_urn = security.HuntApprovalRequestor(
          reason="foo",
          subject_urn=hunt1_urn,
          approver="approver",
          token=self.token).Request()
      approval1_id = approval_urn.Basename()

    with test_lib.FakeTime(45):
      approval_urn = security.HuntApprovalRequestor(
          reason="bar",
          subject_urn=hunt2_urn,
          approver="approver",
          token=self.token).Request()
      approval2_id = approval_urn.Basename()

    with test_lib.FakeTime(84):
      approver_token = access_control.ACLToken(username="approver")
      security.HuntApprovalGrantor(
          reason="bar",
          delegate=self.token.username,
          subject_urn=hunt2_urn,
          token=approver_token).Grant()

    with test_lib.FakeTime(126):
      self.Check(
          "GetHuntApproval",
          args=user_plugin.ApiGetHuntApprovalArgs(
              username=self.token.username,
              hunt_id=hunt1_id,
              approval_id=approval1_id),
          replace={
              hunt1_id: "H:123456",
              approval1_id: "approval:111111"
          })
      self.Check(
          "GetHuntApproval",
          args=user_plugin.ApiGetHuntApprovalArgs(
              username=self.token.username,
              hunt_id=hunt2_id,
              approval_id=approval2_id),
          replace={
              hunt2_id: "H:567890",
              approval2_id: "approval:222222"
          })

  def _RunTestForApprovalForHuntCopiedFromAnotherHunt(self):
    with test_lib.FakeTime(42):
      self.CreateAdminUser("approver")

      with self.CreateHunt(description="original hunt") as hunt_obj:
        hunt1_urn = hunt_obj.urn
        hunt1_id = hunt1_urn.Basename()

      ref = rdf_hunts.FlowLikeObjectReference.FromHuntId(hunt1_id)
      with self.CreateHunt(
          description="copied hunt", original_object=ref) as hunt_obj:
        hunt2_urn = hunt_obj.urn
        hunt2_id = hunt2_urn.Basename()

    with test_lib.FakeTime(44):
      approval_urn = security.HuntApprovalRequestor(
          reason="foo",
          subject_urn=hunt2_urn,
          approver="approver",
          token=self.token).Request()
      approval_id = approval_urn.Basename()

    with test_lib.FakeTime(126):
      self.Check(
          "GetHuntApproval",
          args=user_plugin.ApiGetHuntApprovalArgs(
              username=self.token.username,
              hunt_id=hunt2_id,
              approval_id=approval_id),
          replace={
              hunt1_id: "H:556677",
              hunt2_id: "H:DDEEFF",
              approval_id: "approval:333333"
          })

  def _RunTestForApprovalForHuntCopiedFromFlow(self):
    with test_lib.FakeTime(42):
      self.CreateAdminUser("approver")

      client_urn = self.SetupClient(0)
      flow_urn = flow.GRRFlow.StartFlow(
          flow_name=discovery.Interrogate.__name__,
          client_id=client_urn,
          token=self.token)

      ref = rdf_hunts.FlowLikeObjectReference.FromFlowIdAndClientId(
          flow_urn.Basename(), client_urn.Basename())
      with self.CreateHunt(
          description="hunt started from flow",
          original_object=ref) as hunt_obj:
        hunt_urn = hunt_obj.urn
        hunt_id = hunt_urn.Basename()

    with test_lib.FakeTime(44):
      approval_urn = security.HuntApprovalRequestor(
          reason="foo",
          subject_urn=hunt_urn,
          approver="approver",
          token=self.token).Request()
      approval_id = approval_urn.Basename()

    with test_lib.FakeTime(126):
      self.Check(
          "GetHuntApproval",
          args=user_plugin.ApiGetHuntApprovalArgs(
              username=self.token.username,
              hunt_id=hunt_id,
              approval_id=approval_id),
          replace={
              flow_urn.Basename(): "F:112233",
              hunt_id: "H:667788",
              approval_id: "approval:444444"
          })

  def Run(self):
    self._RunTestForNormalApprovals()
    self._RunTestForApprovalForHuntCopiedFromAnotherHunt()
    self._RunTestForApprovalForHuntCopiedFromFlow()


class ApiGrantHuntApprovalHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest,
    standard_test.StandardHuntTestMixin, acl_test_lib.AclTestMixin):
  """Regression test for ApiGrantHuntApprovalHandler."""

  api_method = "GrantHuntApproval"
  handler = user_plugin.ApiGrantHuntApprovalHandler

  def Run(self):
    with test_lib.FakeTime(42):
      self.CreateAdminUser("requestor")

      with self.CreateHunt(description="a hunt") as hunt_obj:
        hunt_urn = hunt_obj.urn
        hunt_id = hunt_urn.Basename()

    with test_lib.FakeTime(44):
      requestor_token = access_control.ACLToken(username="requestor")
      approval_urn = security.HuntApprovalRequestor(
          reason="foo",
          subject_urn=hunt_urn,
          approver=self.token.username,
          token=requestor_token).Request()
      approval_id = approval_urn.Basename()

    with test_lib.FakeTime(126):
      self.Check(
          "GrantHuntApproval",
          args=user_plugin.ApiGrantHuntApprovalArgs(
              hunt_id=hunt_id, approval_id=approval_id, username="requestor"),
          replace={
              hunt_id: "H:123456",
              approval_id: "approval:111111"
          })


class ApiCreateHuntApprovalHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest,
    standard_test.StandardHuntTestMixin, acl_test_lib.AclTestMixin):
  """Regression test for ApiCreateHuntApprovalHandler."""

  api_method = "CreateHuntApproval"
  handler = user_plugin.ApiCreateHuntApprovalHandler

  def Run(self):
    with test_lib.FakeTime(42):
      self.CreateUser("approver")

      with self.CreateHunt(description="foo") as hunt_obj:
        hunt_id = hunt_obj.urn.Basename()

    def ReplaceHuntAndApprovalIds():
      approvals = list(
          aff4.FACTORY.ListChildren(
              aff4.ROOT_URN.Add("ACL").Add("hunts").Add(hunt_id).Add(
                  self.token.username)))

      return {approvals[0].Basename(): "approval:112233", hunt_id: "H:123456"}

    with test_lib.FakeTime(126):
      self.Check(
          "CreateHuntApproval",
          args=user_plugin.ApiCreateHuntApprovalArgs(
              hunt_id=hunt_id,
              approval=user_plugin.ApiHuntApproval(
                  reason="really important reason!",
                  notified_users=["approver1", "approver2"],
                  email_cc_addresses=["test@example.com"])),
          replace=ReplaceHuntAndApprovalIds)


class ApiListHuntApprovalsHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest, acl_test_lib.AclTestMixin):
  """Regression test for ApiListClientApprovalsHandlerTest."""

  api_method = "ListHuntApprovals"
  handler = user_plugin.ApiListHuntApprovalsHandler

  def Run(self):
    with test_lib.FakeTime(42):
      self.CreateAdminUser("approver")

      hunt = implementation.GRRHunt.StartHunt(
          hunt_name=standard.GenericHunt.__name__, token=self.token)

    with test_lib.FakeTime(43):
      approval_urn = security.HuntApprovalRequestor(
          reason=self.token.reason,
          subject_urn=hunt.urn,
          approver="approver",
          token=self.token).Request()
      approval_id = approval_urn.Basename()

    with test_lib.FakeTime(126):
      self.Check(
          "ListHuntApprovals",
          replace={
              hunt.urn.Basename(): "H:123456",
              approval_id: "approval:112233"
          })


class ApiGetCronJobApprovalHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest, acl_test_lib.AclTestMixin):
  """Regression test for ApiGetCronJobApprovalHandler."""

  api_method = "GetCronJobApproval"
  handler = user_plugin.ApiGetCronJobApprovalHandler

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
      approval_urn = security.CronJobApprovalRequestor(
          reason="foo",
          subject_urn=cron1_urn,
          approver="approver",
          token=self.token).Request()
      approval1_id = approval_urn.Basename()

    with test_lib.FakeTime(45):
      approval_urn = security.CronJobApprovalRequestor(
          reason="bar",
          subject_urn=cron2_urn,
          approver="approver",
          token=self.token).Request()
      approval2_id = approval_urn.Basename()

    with test_lib.FakeTime(84):
      approver_token = access_control.ACLToken(username="approver")
      security.CronJobApprovalGrantor(
          reason="bar",
          delegate=self.token.username,
          subject_urn=cron2_urn,
          token=approver_token).Grant()

    with test_lib.FakeTime(126):
      self.Check(
          "GetCronJobApproval",
          args=user_plugin.ApiGetCronJobApprovalArgs(
              username=self.token.username,
              cron_job_id=cron1_urn.Basename(),
              approval_id=approval1_id),
          replace={
              cron1_urn.Basename(): "CronJob_123456",
              approval1_id: "approval:111111"
          })
      self.Check(
          "GetCronJobApproval",
          args=user_plugin.ApiGetCronJobApprovalArgs(
              username=self.token.username,
              cron_job_id=cron2_urn.Basename(),
              approval_id=approval2_id),
          replace={
              cron2_urn.Basename(): "CronJob_567890",
              approval2_id: "approval:222222"
          })


class ApiGrantCronJobApprovalHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest, acl_test_lib.AclTestMixin):
  """Regression test for ApiGrantCronJobApprovalHandler."""

  api_method = "GrantCronJobApproval"
  handler = user_plugin.ApiGrantCronJobApprovalHandler

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
      approval_urn = security.CronJobApprovalRequestor(
          reason="foo",
          subject_urn=cron_urn,
          approver=self.token.username,
          token=requestor_token).Request()
      approval_id = approval_urn.Basename()

    with test_lib.FakeTime(126):
      self.Check(
          "GrantCronJobApproval",
          args=user_plugin.ApiGrantCronJobApprovalArgs(
              cron_job_id=cron_urn.Basename(),
              approval_id=approval_id,
              username="requestor"),
          replace={
              cron_urn.Basename(): "CronJob_123456",
              approval_id: "approval:111111"
          })


class ApiCreateCronJobApprovalHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest, acl_test_lib.AclTestMixin):
  """Regression test for ApiCreateCronJobApprovalHandler."""

  api_method = "CreateCronJobApproval"
  handler = user_plugin.ApiCreateCronJobApprovalHandler

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
                  self.token.username)))

      return {
          approvals[0].Basename(): "approval:112233",
          cron_id: "CronJob_123456"
      }

    with test_lib.FakeTime(126):
      self.Check(
          "CreateCronJobApproval",
          args=user_plugin.ApiCreateCronJobApprovalArgs(
              cron_job_id=cron_id,
              approval=user_plugin.ApiCronJobApproval(
                  reason="really important reason!",
                  notified_users=["approver1", "approver2"],
                  email_cc_addresses=["test@example.com"])),
          replace=ReplaceCronAndApprovalIds)


class ApiGetOwnGrrUserHandlerRegresstionTest(
    api_regression_test_lib.ApiRegressionTest):
  """Regression test for ApiGetUserSettingsHandler."""

  api_method = "GetGrrUser"
  handler = user_plugin.ApiGetOwnGrrUserHandler

  def Run(self):
    user_urn = aff4.ROOT_URN.Add("users").Add(self.token.username)
    with test_lib.FakeTime(42):
      with aff4.FACTORY.Create(
          user_urn, aff4_type=aff4_users.GRRUser, mode="w",
          token=self.token) as user_fd:
        user_fd.Set(
            user_fd.Schema.GUI_SETTINGS,
            aff4_users.GUISettings(canary_mode=True))

    # Setup relational DB.
    data_store.REL_DB.WriteGRRUser(
        username=self.token.username, canary_mode=True)

    self.Check("GetGrrUser")

    # Make user an admin and do yet another request.
    with aff4.FACTORY.Open(user_urn, mode="rw", token=self.token) as user_fd:
      user_fd.SetLabel("admin", owner="GRR")
    data_store.REL_DB.WriteGRRUser(
        username=self.token.username,
        user_type=rdf_objects.GRRUser.UserType.USER_TYPE_ADMIN)

    self.Check("GetGrrUser")


class ApiGetPendingUserNotificationsCountHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest):
  """Regression test for ApiGetPendingUserNotificationsCountHandler."""

  api_method = "GetPendingUserNotificationsCount"
  handler = user_plugin.ApiGetPendingUserNotificationsCountHandler

  def setUp(self):
    super(ApiGetPendingUserNotificationsCountHandlerRegressionTest,
          self).setUp()
    self.client_id = self.SetupClient(0)

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

    self.Check("GetPendingUserNotificationsCount")


class ApiListPendingUserNotificationsHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest):
  """Regression test for ApiListPendingUserNotificationsHandler."""

  api_method = "ListPendingUserNotifications"
  handler = user_plugin.ApiListPendingUserNotificationsHandler

  def setUp(self):
    super(ApiListPendingUserNotificationsHandlerRegressionTest, self).setUp()
    self.client_id = self.SetupClient(0)

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

    self.Check(
        "ListPendingUserNotifications",
        args=user_plugin.ApiListPendingUserNotificationsArgs())
    self.Check(
        "ListPendingUserNotifications",
        args=user_plugin.ApiListPendingUserNotificationsArgs(
            timestamp=43000000))


class ApiListAndResetUserNotificationsHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest):
  """Regression test for ApiListAndResetUserNotificationsHandler."""

  api_method = "ListAndResetUserNotifications"
  handler = user_plugin.ApiListAndResetUserNotificationsHandler

  def setUp(self):
    super(ApiListAndResetUserNotificationsHandlerRegressionTest, self).setUp()
    self.client_id = self.SetupClient(0)

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
    self.Check(
        "ListAndResetUserNotifications",
        args=user_plugin.ApiListAndResetUserNotificationsArgs())

    # But not anymore in these requests.
    self.Check(
        "ListAndResetUserNotifications",
        args=user_plugin.ApiListAndResetUserNotificationsArgs(
            offset=1, count=1))
    self.Check(
        "ListAndResetUserNotifications",
        args=user_plugin.ApiListAndResetUserNotificationsArgs(filter="other"))


class ApiListPendingGlobalNotificationsHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest):
  """Regression test for ApiListPendingGlobalNotificationsHandler."""

  api_method = "ListPendingGlobalNotifications"
  handler = user_plugin.ApiListPendingGlobalNotificationsHandler

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

    replace = {
        ("%d" % self.TIME_0.AsMicroSecondsFromEpoch()): "0",
        ("%d" % self.TIME_1.AsMicroSecondsFromEpoch()): "0"
    }

    self.Check("ListPendingGlobalNotifications", replace=replace)


def main(argv):
  api_regression_test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
