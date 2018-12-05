#!/usr/bin/env python
"""This module contains regression tests for user API handlers."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib import flags

from grr_response_server import aff4
from grr_response_server import data_store
from grr_response_server import notification
from grr_response_server.aff4_objects import cronjobs as aff4_cronjobs
from grr_response_server.aff4_objects import users as aff4_users
from grr_response_server.flows.general import discovery
from grr_response_server.gui import api_regression_test_lib
from grr_response_server.gui.api_plugins import user as user_plugin
from grr_response_server.hunts import implementation
from grr_response_server.hunts import standard
from grr_response_server.rdfvalues import cronjobs as rdf_cronjobs
from grr_response_server.rdfvalues import hunts as rdf_hunts
from grr_response_server.rdfvalues import objects as rdf_objects

from grr.test_lib import acl_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import hunt_test_lib
from grr.test_lib import test_lib


class ApiGetClientApprovalHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest, acl_test_lib.AclTestMixin):
  """Regression test for ApiGetClientApprovalHandler."""

  api_method = "GetClientApproval"
  handler = user_plugin.ApiGetClientApprovalHandler

  def Run(self):
    with test_lib.FakeTime(42):
      self.CreateAdminUser(u"approver")

      clients = self.SetupClients(2)
      for client_id in clients:
        # Delete the certificate as it's being regenerated every time the
        # client is created.
        with aff4.FACTORY.Open(
            client_id, mode="rw", token=self.token) as grr_client:
          grr_client.DeleteAttribute(grr_client.Schema.CERT)

    with test_lib.FakeTime(44):
      approval1_id = self.RequestClientApproval(
          clients[0].Basename(),
          reason="foo",
          approver=u"approver",
          requestor=self.token.username)

    with test_lib.FakeTime(45):
      approval2_id = self.RequestClientApproval(
          clients[1].Basename(),
          reason="bar",
          approver=u"approver",
          requestor=self.token.username)

    with test_lib.FakeTime(84):
      self.GrantClientApproval(
          clients[1].Basename(),
          approval_id=approval2_id,
          approver=u"approver",
          requestor=self.token.username)

    with test_lib.FakeTime(126):
      self.Check(
          "GetClientApproval",
          args=user_plugin.ApiGetClientApprovalArgs(
              client_id=clients[0].Basename(),
              approval_id=approval1_id,
              username=self.token.username),
          replace={approval1_id: "approval:111111"})
      self.Check(
          "GetClientApproval",
          args=user_plugin.ApiGetClientApprovalArgs(
              client_id=clients[1].Basename(),
              approval_id=approval2_id,
              username=self.token.username),
          replace={approval2_id: "approval:222222"})


class ApiGrantClientApprovalHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest, acl_test_lib.AclTestMixin):
  """Regression test for ApiGrantClientApprovalHandler."""

  api_method = "GrantClientApproval"
  handler = user_plugin.ApiGrantClientApprovalHandler

  def Run(self):
    with test_lib.FakeTime(42):
      self.CreateAdminUser(u"requestor")

      client_id = self.SetupClient(0)
      # Delete the certificate as it's being regenerated every time the
      # client is created.
      with aff4.FACTORY.Open(
          client_id, mode="rw", token=self.token) as grr_client:
        grr_client.DeleteAttribute(grr_client.Schema.CERT)

    with test_lib.FakeTime(44):
      approval_id = self.RequestClientApproval(
          client_id.Basename(),
          reason="foo",
          approver=self.token.username,
          requestor=u"requestor")

    with test_lib.FakeTime(126):
      self.Check(
          "GrantClientApproval",
          args=user_plugin.ApiGrantClientApprovalArgs(
              client_id=client_id.Basename(),
              approval_id=approval_id,
              username=u"requestor"),
          replace={approval_id: "approval:111111"})


class ApiCreateClientApprovalHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest, acl_test_lib.AclTestMixin):
  """Regression test for ApiCreateClientApprovalHandler."""

  api_method = "CreateClientApproval"
  handler = user_plugin.ApiCreateClientApprovalHandler

  def Run(self):
    with test_lib.FakeTime(42):
      self.CreateUser(u"approver")

      client_id = self.SetupClient(0)

      # Delete the certificate as it's being regenerated every time the
      # client is created.
      with aff4.FACTORY.Open(
          client_id, mode="rw", token=self.token) as grr_client:
        grr_client.DeleteAttribute(grr_client.Schema.CERT)

    def ReplaceApprovalId():
      approvals = self.ListClientApprovals()
      return {approvals[0].id: "approval:112233"}

    with test_lib.FakeTime(126):
      self.Check(
          "CreateClientApproval",
          args=user_plugin.ApiCreateClientApprovalArgs(
              client_id=client_id.Basename(),
              approval=user_plugin.ApiClientApproval(
                  reason="really important reason!",
                  notified_users=[u"approver1", u"approver2"],
                  email_cc_addresses=["test@example.com"])),
          replace=ReplaceApprovalId)


class ApiListClientApprovalsHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest, acl_test_lib.AclTestMixin):
  """Regression test for ApiListClientApprovalsHandlerTest."""

  api_method = "ListClientApprovals"
  handler = user_plugin.ApiListClientApprovalsHandler

  def Run(self):
    with test_lib.FakeTime(42):
      self.CreateAdminUser(u"approver")

      clients = self.SetupClients(2)
      for client_id in clients:
        # Delete the certificate as it's being regenerated every time the
        # client is created.
        with aff4.FACTORY.Open(
            client_id, mode="rw", token=self.token) as grr_client:
          grr_client.DeleteAttribute(grr_client.Schema.CERT)

    with test_lib.FakeTime(44):
      approval1_id = self.RequestClientApproval(
          clients[0].Basename(),
          reason=self.token.reason,
          approver=u"approver",
          requestor=self.token.username)

    with test_lib.FakeTime(45):
      approval2_id = self.RequestClientApproval(
          clients[1].Basename(),
          reason=self.token.reason,
          approver=u"approver",
          requestor=self.token.username)

    with test_lib.FakeTime(84):
      self.GrantClientApproval(
          clients[1].Basename(),
          requestor=self.token.username,
          approval_id=approval2_id,
          approver=u"approver")

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
    hunt_test_lib.StandardHuntTestMixin, acl_test_lib.AclTestMixin):
  """Regression test for ApiGetHuntApprovalHandler."""

  api_method = "GetHuntApproval"
  handler = user_plugin.ApiGetHuntApprovalHandler

  def _RunTestForNormalApprovals(self):
    with test_lib.FakeTime(42):
      self.CreateAdminUser(u"approver")

      with self.CreateHunt(description="hunt1") as hunt_obj:
        hunt1_id = hunt_obj.urn.Basename()

      with self.CreateHunt(description="hunt2") as hunt_obj:
        hunt2_id = hunt_obj.urn.Basename()

    with test_lib.FakeTime(44):
      approval1_id = self.RequestHuntApproval(
          hunt1_id, approver=u"approver", reason="foo")

    with test_lib.FakeTime(45):
      approval2_id = self.RequestHuntApproval(
          hunt2_id, approver=u"approver", reason="bar")

    with test_lib.FakeTime(84):
      self.GrantHuntApproval(
          hunt2_id, approver=u"approver", approval_id=approval2_id)

    with test_lib.FakeTime(126):
      self.Check(
          "GetHuntApproval",
          args=user_plugin.ApiGetHuntApprovalArgs(
              username=self.token.username,
              hunt_id=hunt1_id,
              approval_id=approval1_id),
          replace={
              hunt1_id: "H:123456",
              approval1_id: "approval:111111",
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
      self.CreateAdminUser(u"approver")

      with self.CreateHunt(description="original hunt") as hunt_obj:
        hunt1_urn = hunt_obj.urn
        hunt1_id = hunt1_urn.Basename()

      ref = rdf_hunts.FlowLikeObjectReference.FromHuntId(hunt1_id)
      with self.CreateHunt(
          description="copied hunt", original_object=ref) as hunt_obj:
        hunt2_urn = hunt_obj.urn
        hunt2_id = hunt2_urn.Basename()

    with test_lib.FakeTime(44):
      approval_id = self.RequestHuntApproval(
          hunt2_id, reason="foo", approver=u"approver")

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
      self.CreateAdminUser(u"approver")

      client_urn = self.SetupClient(0)
      flow_id = flow_test_lib.StartFlow(
          discovery.Interrogate,
          client_id=client_urn,
          creator=self.token.username,
          notify_to_user=True)

      ref = rdf_hunts.FlowLikeObjectReference.FromFlowIdAndClientId(
          flow_id, client_urn.Basename())
      with self.CreateHunt(
          description="hunt started from flow",
          original_object=ref) as hunt_obj:
        hunt_urn = hunt_obj.urn
        hunt_id = hunt_urn.Basename()

    with test_lib.FakeTime(44):
      approval_id = self.RequestHuntApproval(
          hunt_id, reason="foo", approver=u"approver")

    with test_lib.FakeTime(126):
      self.Check(
          "GetHuntApproval",
          args=user_plugin.ApiGetHuntApprovalArgs(
              username=self.token.username,
              hunt_id=hunt_id,
              approval_id=approval_id),
          replace={
              # TODO(user): remove this replacement as soon as REL_DB
              # migration is done.
              "%s/%s" % (client_urn.Basename(), flow_id):
                  "%s/flows/F:112233" % (client_urn.Basename()),
              flow_id:
                  "F:112233",
              hunt_id:
                  "H:667788",
              approval_id:
                  "approval:444444"
          })

  def Run(self):
    self._RunTestForNormalApprovals()
    self._RunTestForApprovalForHuntCopiedFromAnotherHunt()
    self._RunTestForApprovalForHuntCopiedFromFlow()


class ApiGrantHuntApprovalHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest,
    hunt_test_lib.StandardHuntTestMixin, acl_test_lib.AclTestMixin):
  """Regression test for ApiGrantHuntApprovalHandler."""

  api_method = "GrantHuntApproval"
  handler = user_plugin.ApiGrantHuntApprovalHandler

  def Run(self):
    with test_lib.FakeTime(42):
      self.CreateAdminUser(u"requestor")

      with self.CreateHunt(description="a hunt") as hunt_obj:
        hunt_urn = hunt_obj.urn
        hunt_id = hunt_urn.Basename()

    with test_lib.FakeTime(44):
      approval_id = self.RequestHuntApproval(
          hunt_id,
          requestor=u"requestor",
          reason="foo",
          approver=self.token.username)

    with test_lib.FakeTime(126):
      self.Check(
          "GrantHuntApproval",
          args=user_plugin.ApiGrantHuntApprovalArgs(
              hunt_id=hunt_id, approval_id=approval_id, username=u"requestor"),
          replace={
              hunt_id: "H:123456",
              approval_id: "approval:111111"
          })


class ApiCreateHuntApprovalHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest,
    hunt_test_lib.StandardHuntTestMixin, acl_test_lib.AclTestMixin):
  """Regression test for ApiCreateHuntApprovalHandler."""

  api_method = "CreateHuntApproval"
  handler = user_plugin.ApiCreateHuntApprovalHandler

  def Run(self):
    with test_lib.FakeTime(42):
      self.CreateUser(u"approver")

      with self.CreateHunt(description="foo") as hunt_obj:
        hunt_id = hunt_obj.urn.Basename()

    def ReplaceHuntAndApprovalIds():
      approvals = self.ListHuntApprovals()
      return {approvals[0].id: "approval:112233", hunt_id: "H:123456"}

    with test_lib.FakeTime(126):
      self.Check(
          "CreateHuntApproval",
          args=user_plugin.ApiCreateHuntApprovalArgs(
              hunt_id=hunt_id,
              approval=user_plugin.ApiHuntApproval(
                  reason="really important reason!",
                  notified_users=[u"approver1", u"approver2"],
                  email_cc_addresses=["test@example.com"])),
          replace=ReplaceHuntAndApprovalIds)


class ApiListHuntApprovalsHandlerRegressionTest(
    acl_test_lib.AclTestMixin, api_regression_test_lib.ApiRegressionTest):
  """Regression test for ApiListClientApprovalsHandlerTest."""

  api_method = "ListHuntApprovals"
  handler = user_plugin.ApiListHuntApprovalsHandler

  def Run(self):
    with test_lib.FakeTime(42):
      self.CreateAdminUser(u"approver")

      hunt = implementation.StartHunt(
          hunt_name=standard.GenericHunt.__name__, token=self.token)

    with test_lib.FakeTime(43):
      approval_id = self.RequestHuntApproval(
          hunt.urn.Basename(),
          reason=self.token.reason,
          approver=u"approver",
          requestor=self.token.username)

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
      self.CreateAdminUser(u"approver")

      cron_manager = aff4_cronjobs.GetCronManager()
      cron_args = rdf_cronjobs.CreateCronJobArgs(
          frequency="1d", allow_overruns=False)

      cron1_id = cron_manager.CreateJob(cron_args=cron_args, token=self.token)
      cron2_id = cron_manager.CreateJob(cron_args=cron_args, token=self.token)

    with test_lib.FakeTime(44):
      approval1_id = self.RequestCronJobApproval(
          cron1_id, reason="foo", approver=u"approver")

    with test_lib.FakeTime(45):
      approval2_id = self.RequestCronJobApproval(
          cron2_id, reason="bar", approver=u"approver")

    with test_lib.FakeTime(84):
      self.GrantCronJobApproval(
          cron2_id, approval_id=approval2_id, approver=u"approver")

    with test_lib.FakeTime(126):
      self.Check(
          "GetCronJobApproval",
          args=user_plugin.ApiGetCronJobApprovalArgs(
              username=self.token.username,
              cron_job_id=cron1_id,
              approval_id=approval1_id),
          replace={
              cron1_id: "CronJob_123456",
              approval1_id: "approval:111111"
          })
      self.Check(
          "GetCronJobApproval",
          args=user_plugin.ApiGetCronJobApprovalArgs(
              username=self.token.username,
              cron_job_id=cron2_id,
              approval_id=approval2_id),
          replace={
              cron2_id: "CronJob_567890",
              approval2_id: "approval:222222"
          })


class ApiGrantCronJobApprovalHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest, acl_test_lib.AclTestMixin):
  """Regression test for ApiGrantCronJobApprovalHandler."""

  api_method = "GrantCronJobApproval"
  handler = user_plugin.ApiGrantCronJobApprovalHandler

  def Run(self):
    with test_lib.FakeTime(42):
      self.CreateAdminUser(u"requestor")

      cron_manager = aff4_cronjobs.GetCronManager()
      cron_args = rdf_cronjobs.CreateCronJobArgs(
          frequency="1d", allow_overruns=False)
      cron_id = cron_manager.CreateJob(cron_args=cron_args, token=self.token)

    with test_lib.FakeTime(44):
      approval_id = self.RequestCronJobApproval(
          cron_id,
          approver=self.token.username,
          requestor=u"requestor",
          reason="foo")

    with test_lib.FakeTime(126):
      self.Check(
          "GrantCronJobApproval",
          args=user_plugin.ApiGrantCronJobApprovalArgs(
              cron_job_id=cron_id,
              approval_id=approval_id,
              username=u"requestor"),
          replace={
              cron_id: "CronJob_123456",
              approval_id: "approval:111111"
          })


class ApiCreateCronJobApprovalHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest, acl_test_lib.AclTestMixin):
  """Regression test for ApiCreateCronJobApprovalHandler."""

  api_method = "CreateCronJobApproval"
  handler = user_plugin.ApiCreateCronJobApprovalHandler

  def Run(self):
    with test_lib.FakeTime(42):
      self.CreateUser(u"approver")

    cron_manager = aff4_cronjobs.GetCronManager()
    cron_args = rdf_cronjobs.CreateCronJobArgs(
        frequency="1d", allow_overruns=False)
    cron_id = cron_manager.CreateJob(cron_args=cron_args, token=self.token)

    def ReplaceCronAndApprovalIds():
      approvals = self.ListCronJobApprovals()
      return {approvals[0].id: "approval:112233", cron_id: "CronJob_123456"}

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
        user_fd.Set(user_fd.Schema.GUI_SETTINGS,
                    aff4_users.GUISettings(mode="ADVANCED", canary_mode=True))

    # Setup relational DB.
    data_store.REL_DB.WriteGRRUser(
        username=self.token.username, ui_mode="ADVANCED", canary_mode=True)

    self.Check("GetGrrUser")

    # Make user an admin and do yet another request.
    with aff4.FACTORY.Open(user_urn, mode="rw", token=self.token) as user_fd:
      user_fd.SetLabel("admin", owner="GRR")
    data_store.REL_DB.WriteGRRUser(
        username=self.token.username,
        user_type=rdf_objects.GRRUser.UserType.USER_TYPE_ADMIN)

    self.Check("GetGrrUser")


def _SendNotifications(username, client_id):
  with test_lib.FakeTime(42):
    notification.Notify(
        username, rdf_objects.UserNotification.Type.TYPE_CLIENT_INTERROGATED,
        "<some message>",
        rdf_objects.ObjectReference(
            reference_type=rdf_objects.ObjectReference.Type.CLIENT,
            client=rdf_objects.ClientReference(client_id=client_id.Basename())))

  with test_lib.FakeTime(44):
    notification.Notify(
        username,
        rdf_objects.UserNotification.Type.TYPE_VFS_FILE_COLLECTION_FAILED,
        "<some other message>",
        rdf_objects.ObjectReference(
            reference_type=rdf_objects.ObjectReference.Type.VFS_FILE,
            vfs_file=rdf_objects.VfsFileReference(
                client_id=client_id.Basename(),
                path_type=rdf_objects.PathInfo.PathType.OS,
                path_components=["foo"])))


class ApiGetPendingUserNotificationsCountHandlerRegressionTest(
    acl_test_lib.AclTestMixin, api_regression_test_lib.ApiRegressionTest):
  """Regression test for ApiGetPendingUserNotificationsCountHandler."""

  api_method = "GetPendingUserNotificationsCount"
  handler = user_plugin.ApiGetPendingUserNotificationsCountHandler

  def Run(self):
    client_id = self.SetupClient(0)
    self.CreateUser(self.token.username)
    _SendNotifications(self.token.username, client_id)

    self.Check("GetPendingUserNotificationsCount")


class ApiListPendingUserNotificationsHandlerRegressionTest(
    acl_test_lib.AclTestMixin, api_regression_test_lib.ApiRegressionTest):
  """Regression test for ApiListPendingUserNotificationsHandler."""

  api_method = "ListPendingUserNotifications"
  handler = user_plugin.ApiListPendingUserNotificationsHandler

  def Run(self):
    client_id = self.SetupClient(0)
    self.CreateUser(self.token.username)

    _SendNotifications(self.token.username, client_id)

    self.Check(
        "ListPendingUserNotifications",
        args=user_plugin.ApiListPendingUserNotificationsArgs())
    self.Check(
        "ListPendingUserNotifications",
        args=user_plugin.ApiListPendingUserNotificationsArgs(
            timestamp=43000000))
    self.Check(
        "ListPendingUserNotifications",
        args=user_plugin.ApiListPendingUserNotificationsArgs(
            timestamp=44000000))


class ApiListAndResetUserNotificationsHandlerRegressionTest(
    acl_test_lib.AclTestMixin, api_regression_test_lib.ApiRegressionTest):
  """Regression test for ApiListAndResetUserNotificationsHandler."""

  api_method = "ListAndResetUserNotifications"
  handler = user_plugin.ApiListAndResetUserNotificationsHandler

  def Run(self):
    client_id = self.SetupClient(0)
    self.CreateUser(self.token.username)
    _SendNotifications(self.token.username, client_id)

    # _SendNotifications schedule notifications at timestamp 42 and 44.
    # REL_DB-based ListAndResetUserNotifications implementation only
    # reads last 6 months worth of notifications. Hence - using FakeTime.
    with test_lib.FakeTime(45):
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


class ApiListApproverSuggestionsHandlerRegressionTest(
    acl_test_lib.AclTestMixin, api_regression_test_lib.ApiRegressionTest):
  """Regression test for ApiListApproverSuggestionsHandler."""

  api_method = "ListApproverSuggestions"
  handler = user_plugin.ApiListApproverSuggestionsHandler

  def Run(self):
    self.CreateUser("sanchezmorty")
    self.CreateUser("sanchezrick")
    self.CreateUser("sanchezsummer")

    # Check 0 suggestions, since empty repeated field serialization varies with
    # api version.
    self.Check(
        "ListApproverSuggestions",
        args=user_plugin.ApiListApproverSuggestionsArgs(username_query="foo"))

    # Check formatting of multiple suggestions.
    self.Check(
        "ListApproverSuggestions",
        args=user_plugin.ApiListApproverSuggestionsArgs(
            username_query="sanchez"))


def main(argv):
  api_regression_test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
