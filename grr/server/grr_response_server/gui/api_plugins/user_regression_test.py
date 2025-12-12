#!/usr/bin/env python
"""This module contains regression tests for user API handlers."""

from absl import app

from grr_response_proto import flows_pb2
from grr_response_proto import objects_pb2
from grr_response_proto import user_pb2
from grr_response_proto.api import user_pb2 as api_user_pb2
from grr_response_server import cronjobs
from grr_response_server import data_store
from grr_response_server import notification
from grr_response_server.flows.general import discovery
from grr_response_server.gui import api_regression_test_lib
from grr_response_server.gui.api_plugins import user as user_plugin
from grr_response_server.rdfvalues import cronjobs as rdf_cronjobs
from grr_response_server.rdfvalues import hunts as rdf_hunts
from grr_response_server.rdfvalues import objects as rdf_objects
from grr.test_lib import acl_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import hunt_test_lib
from grr.test_lib import test_lib


class ApiGetClientApprovalHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest, acl_test_lib.AclTestMixin
):
  """Regression test for ApiGetClientApprovalHandler."""

  api_method = "GetClientApproval"
  handler = user_plugin.ApiGetClientApprovalHandler

  def Run(self):
    with test_lib.FakeTime(42):
      self.CreateAdminUser("approver")

      clients = self.SetupClients(2)

    with test_lib.FakeTime(44):
      approval1_id = self.RequestClientApproval(
          clients[0],
          reason="foo",
          approver="approver",
          requestor=self.test_username,
      )

    with test_lib.FakeTime(45):
      approval2_id = self.RequestClientApproval(
          clients[1],
          reason="bar",
          approver="approver",
          requestor=self.test_username,
      )

    with test_lib.FakeTime(84):
      self.GrantClientApproval(
          clients[1],
          approval_id=approval2_id,
          approver="approver",
          requestor=self.test_username,
      )

    with test_lib.FakeTime(126):
      self.Check(
          "GetClientApproval",
          args=api_user_pb2.ApiGetClientApprovalArgs(
              client_id=clients[0],
              approval_id=approval1_id,
              username=self.test_username,
          ),
          replace={approval1_id: "approval:111111"},
      )
      self.Check(
          "GetClientApproval",
          args=api_user_pb2.ApiGetClientApprovalArgs(
              client_id=clients[1],
              approval_id=approval2_id,
              username=self.test_username,
          ),
          replace={approval2_id: "approval:222222"},
      )


class ApiGrantClientApprovalHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest, acl_test_lib.AclTestMixin
):
  """Regression test for ApiGrantClientApprovalHandler."""

  api_method = "GrantClientApproval"
  handler = user_plugin.ApiGrantClientApprovalHandler

  def Run(self):
    with test_lib.FakeTime(42):
      self.CreateAdminUser("requestor")

      client_id = self.SetupClient(0)

    with test_lib.FakeTime(44):
      approval_id = self.RequestClientApproval(
          client_id,
          reason="foo",
          approver=self.test_username,
          requestor="requestor",
      )

    with test_lib.FakeTime(126):
      self.Check(
          "GrantClientApproval",
          args=api_user_pb2.ApiGrantClientApprovalArgs(
              client_id=client_id, approval_id=approval_id, username="requestor"
          ),
          replace={approval_id: "approval:111111"},
      )


class ApiCreateClientApprovalHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest, acl_test_lib.AclTestMixin
):
  """Regression test for ApiCreateClientApprovalHandler."""

  api_method = "CreateClientApproval"
  handler = user_plugin.ApiCreateClientApprovalHandler

  def Run(self):
    with test_lib.FakeTime(42):
      self.CreateUser("approver1")
      self.CreateUser("approver2")
      client_id = self.SetupClient(0)

    def ReplaceApprovalId():
      approvals = self.ListClientApprovals()
      return {approvals[0].id: "approval:112233"}

    with test_lib.FakeTime(126):
      self.Check(
          "CreateClientApproval",
          args=api_user_pb2.ApiCreateClientApprovalArgs(
              client_id=client_id,
              approval=api_user_pb2.ApiClientApproval(
                  reason="really important reason!",
                  notified_users=["approver1", "approver2"],
                  email_cc_addresses=["test@example.com"],
              ),
          ),
          replace=ReplaceApprovalId,
      )


class ApiListClientApprovalsHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest, acl_test_lib.AclTestMixin
):
  """Regression test for ApiListClientApprovalsHandlerTest."""

  api_method = "ListClientApprovals"
  handler = user_plugin.ApiListClientApprovalsHandler

  def Run(self):
    with test_lib.FakeTime(42):
      self.CreateAdminUser("approver")

      clients = self.SetupClients(2)

    with test_lib.FakeTime(44):
      approval1_id = self.RequestClientApproval(
          clients[0],
          reason="Running tests",
          approver="approver",
          requestor=self.test_username,
      )

    with test_lib.FakeTime(45):
      approval2_id = self.RequestClientApproval(
          clients[1],
          reason="Running tests",
          approver="approver",
          requestor=self.test_username,
      )

    with test_lib.FakeTime(84):
      self.GrantClientApproval(
          clients[1],
          requestor=self.test_username,
          approval_id=approval2_id,
          approver="approver",
      )

    with test_lib.FakeTime(126):
      self.Check(
          "ListClientApprovals",
          args=api_user_pb2.ApiListClientApprovalsArgs(),
          replace={
              approval1_id: "approval:111111",
              approval2_id: "approval:222222",
          },
      )
      self.Check(
          "ListClientApprovals",
          args=api_user_pb2.ApiListClientApprovalsArgs(client_id=clients[0]),
          replace={
              approval1_id: "approval:111111",
              approval2_id: "approval:222222",
          },
      )


class ApiGetHuntApprovalHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest,
    hunt_test_lib.StandardHuntTestMixin,
    acl_test_lib.AclTestMixin,
):
  """Regression test for ApiGetHuntApprovalHandler."""

  api_method = "GetHuntApproval"
  handler = user_plugin.ApiGetHuntApprovalHandler

  def _RunTestForNormalApprovals(self):
    with test_lib.FakeTime(42):
      self.CreateAdminUser("approver")

      hunt1_id = self.StartHunt(
          description="hunt1", paused=True, creator=self.test_username
      )
      hunt2_id = self.StartHunt(
          description="hunt2", paused=True, creator=self.test_username
      )

    with test_lib.FakeTime(44):
      approval1_id = self.RequestHuntApproval(
          hunt1_id, approver="approver", reason="foo"
      )

    with test_lib.FakeTime(45):
      approval2_id = self.RequestHuntApproval(
          hunt2_id, approver="approver", reason="bar"
      )

    with test_lib.FakeTime(84):
      self.GrantHuntApproval(
          hunt2_id, approver="approver", approval_id=approval2_id
      )

    with test_lib.FakeTime(126):
      self.Check(
          "GetHuntApproval",
          args=api_user_pb2.ApiGetHuntApprovalArgs(
              username=self.test_username,
              hunt_id=hunt1_id,
              approval_id=approval1_id,
          ),
          replace={
              hunt1_id: "H:123456",
              approval1_id: "approval:111111",
          },
      )
      self.Check(
          "GetHuntApproval",
          args=api_user_pb2.ApiGetHuntApprovalArgs(
              username=self.test_username,
              hunt_id=hunt2_id,
              approval_id=approval2_id,
          ),
          replace={hunt2_id: "H:567890", approval2_id: "approval:222222"},
      )

  def _RunTestForApprovalForHuntCopiedFromAnotherHunt(self):
    with test_lib.FakeTime(42):
      self.CreateAdminUser("approver")

      hunt1_id = self.StartHunt(
          description="original hunt", paused=True, creator=self.test_username
      )

      ref = rdf_hunts.FlowLikeObjectReference.FromHuntId(hunt1_id)
      hunt2_id = self.StartHunt(
          description="copied hunt",
          original_object=ref,
          paused=True,
          creator=self.test_username,
      )

    with test_lib.FakeTime(44):
      approval_id = self.RequestHuntApproval(
          hunt2_id, reason="foo", approver="approver"
      )

    with test_lib.FakeTime(126):
      self.Check(
          "GetHuntApproval",
          args=api_user_pb2.ApiGetHuntApprovalArgs(
              username=self.test_username,
              hunt_id=hunt2_id,
              approval_id=approval_id,
          ),
          replace={
              hunt1_id: "H:556677",
              hunt2_id: "H:DDEEFF",
              approval_id: "approval:333333",
          },
      )

  def _RunTestForApprovalForHuntCopiedFromFlow(self):
    with test_lib.FakeTime(42):
      self.CreateAdminUser("approver")

      client_id = self.SetupClient(0)
      flow_id = flow_test_lib.StartFlow(
          discovery.Interrogate,
          client_id=client_id,
          creator=self.test_username,
      )

      # ApiV1 (RDFValues) serializes the `store` field in the flow object in the
      # database as bytes. The `store` here contains the source flow id, and
      # thus, the bytes change on every run.
      # To avoid this, we update the `store` field in the flow object in the
      # database, so it has an empty store.
      flow_obj = data_store.REL_DB.ReadFlowObject(client_id, flow_id)
      interrogate_store = flows_pb2.InterrogateStore()
      flow_obj.store.Unpack(interrogate_store)
      want_store = flows_pb2.InterrogateStore(
          client_snapshot=objects_pb2.ClientSnapshot(
              client_id=client_id,
              metadata=objects_pb2.ClientSnapshotMetadata(
                  source_flow_id=flow_id
              ),
          )
      )
      self.assertEqual(want_store, interrogate_store)
      api_regression_test_lib.UpdateFlowStore(
          client_id, flow_id, flows_pb2.InterrogateStore()
      )

      # Start a hunt from the flow.
      ref = rdf_hunts.FlowLikeObjectReference.FromFlowIdAndClientId(
          flow_id, client_id
      )
      hunt_id = self.StartHunt(
          description="hunt started from flow",
          original_object=ref,
          paused=True,
          creator=self.test_username,
      )

    with test_lib.FakeTime(44):
      approval_id = self.RequestHuntApproval(
          hunt_id, reason="foo", approver="approver"
      )

    with test_lib.FakeTime(126):
      self.Check(
          "GetHuntApproval",
          args=api_user_pb2.ApiGetHuntApprovalArgs(
              username=self.test_username,
              hunt_id=hunt_id,
              approval_id=approval_id,
          ),
          replace={
              # TODO(user): remove this replacement as soon as REL_DB
              # migration is done.
              "%s/%s" % (client_id, flow_id): "%s/flows/F:112233" % (client_id),
              flow_id: "F:112233",
              hunt_id: "H:667788",
              approval_id: "approval:444444",
          },
      )

  def Run(self):
    self._RunTestForNormalApprovals()
    self._RunTestForApprovalForHuntCopiedFromAnotherHunt()
    self._RunTestForApprovalForHuntCopiedFromFlow()


class ApiGrantHuntApprovalHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest,
    hunt_test_lib.StandardHuntTestMixin,
    acl_test_lib.AclTestMixin,
):
  """Regression test for ApiGrantHuntApprovalHandler."""

  api_method = "GrantHuntApproval"
  handler = user_plugin.ApiGrantHuntApprovalHandler

  def Run(self):
    with test_lib.FakeTime(42):
      self.CreateAdminUser("requestor")
      hunt_id = self.StartHunt(
          description="a hunt", paused=True, creator=self.test_username
      )

    with test_lib.FakeTime(44):
      approval_id = self.RequestHuntApproval(
          hunt_id,
          requestor="requestor",
          reason="foo",
          approver=self.test_username,
      )

    with test_lib.FakeTime(126):
      self.Check(
          "GrantHuntApproval",
          args=api_user_pb2.ApiGrantHuntApprovalArgs(
              hunt_id=hunt_id, approval_id=approval_id, username="requestor"
          ),
          replace={hunt_id: "H:123456", approval_id: "approval:111111"},
      )


class ApiCreateHuntApprovalHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest,
    hunt_test_lib.StandardHuntTestMixin,
    acl_test_lib.AclTestMixin,
):
  """Regression test for ApiCreateHuntApprovalHandler."""

  api_method = "CreateHuntApproval"
  handler = user_plugin.ApiCreateHuntApprovalHandler

  def Run(self):
    with test_lib.FakeTime(42):
      self.CreateUser("approver1")
      self.CreateUser("approver2")
      hunt_id = self.StartHunt(
          description="foo", paused=True, creator=self.test_username
      )

    def ReplaceHuntAndApprovalIds():
      approvals = self.ListHuntApprovals()
      return {approvals[0].id: "approval:112233", hunt_id: "H:123456"}

    with test_lib.FakeTime(126):
      self.Check(
          "CreateHuntApproval",
          args=api_user_pb2.ApiCreateHuntApprovalArgs(
              hunt_id=hunt_id,
              approval=api_user_pb2.ApiHuntApproval(
                  reason="really important reason!",
                  notified_users=["approver1", "approver2"],
                  email_cc_addresses=["test@example.com"],
              ),
          ),
          replace=ReplaceHuntAndApprovalIds,
      )


class ApiListHuntApprovalsHandlerRegressionTest(
    hunt_test_lib.StandardHuntTestMixin,
    api_regression_test_lib.ApiRegressionTest,
):
  """Regression test for ApiListClientApprovalsHandlerTest."""

  api_method = "ListHuntApprovals"
  handler = user_plugin.ApiListHuntApprovalsHandler

  def Run(self):
    with test_lib.FakeTime(42):
      self.CreateAdminUser("approver")
      hunt_id = self.StartHunt(
          description="foo", paused=True, creator=self.test_username
      )

    with test_lib.FakeTime(43):
      approval_id = self.RequestHuntApproval(
          hunt_id,
          reason="Running tests",
          approver="approver",
          requestor=self.test_username,
      )

    with test_lib.FakeTime(126):
      self.Check(
          "ListHuntApprovals",
          replace={hunt_id: "H:123456", approval_id: "approval:112233"},
      )


class ApiGetCronJobApprovalHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest, acl_test_lib.AclTestMixin
):
  """Regression test for ApiGetCronJobApprovalHandler."""

  api_method = "GetCronJobApproval"
  handler = user_plugin.ApiGetCronJobApprovalHandler

  def Run(self):
    with test_lib.FakeTime(42):
      self.CreateAdminUser("approver")

      cron_manager = cronjobs.CronManager()
      cron_args = rdf_cronjobs.CreateCronJobArgs(
          frequency="1d",
          allow_overruns=False,
          flow_name=discovery.Interrogate.__name__,
      )

      cron1_id = cron_manager.CreateJob(cron_args=cron_args)
      cron2_id = cron_manager.CreateJob(cron_args=cron_args)

    with test_lib.FakeTime(44):
      approval1_id = self.RequestCronJobApproval(
          cron1_id, reason="foo", approver="approver"
      )

    with test_lib.FakeTime(45):
      approval2_id = self.RequestCronJobApproval(
          cron2_id, reason="bar", approver="approver"
      )

    with test_lib.FakeTime(84):
      self.GrantCronJobApproval(
          cron2_id, approval_id=approval2_id, approver="approver"
      )

    with test_lib.FakeTime(126):
      self.Check(
          "GetCronJobApproval",
          args=api_user_pb2.ApiGetCronJobApprovalArgs(
              username=self.test_username,
              cron_job_id=cron1_id,
              approval_id=approval1_id,
          ),
          replace={cron1_id: "CronJob_123456", approval1_id: "approval:111111"},
      )
      self.Check(
          "GetCronJobApproval",
          args=api_user_pb2.ApiGetCronJobApprovalArgs(
              username=self.test_username,
              cron_job_id=cron2_id,
              approval_id=approval2_id,
          ),
          replace={cron2_id: "CronJob_567890", approval2_id: "approval:222222"},
      )


class ApiGrantCronJobApprovalHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest, acl_test_lib.AclTestMixin
):
  """Regression test for ApiGrantCronJobApprovalHandler."""

  api_method = "GrantCronJobApproval"
  handler = user_plugin.ApiGrantCronJobApprovalHandler

  def Run(self):
    with test_lib.FakeTime(42):
      self.CreateAdminUser("requestor")

      cron_manager = cronjobs.CronManager()
      cron_args = rdf_cronjobs.CreateCronJobArgs(
          frequency="1d",
          allow_overruns=False,
          flow_name=discovery.Interrogate.__name__,
      )
      cron_id = cron_manager.CreateJob(cron_args=cron_args)

    with test_lib.FakeTime(44):
      approval_id = self.RequestCronJobApproval(
          cron_id,
          approver=self.test_username,
          requestor="requestor",
          reason="foo",
      )

    with test_lib.FakeTime(126):
      self.Check(
          "GrantCronJobApproval",
          args=api_user_pb2.ApiGrantCronJobApprovalArgs(
              cron_job_id=cron_id, approval_id=approval_id, username="requestor"
          ),
          replace={cron_id: "CronJob_123456", approval_id: "approval:111111"},
      )


class ApiCreateCronJobApprovalHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest, acl_test_lib.AclTestMixin
):
  """Regression test for ApiCreateCronJobApprovalHandler."""

  api_method = "CreateCronJobApproval"
  handler = user_plugin.ApiCreateCronJobApprovalHandler

  def Run(self):
    with test_lib.FakeTime(42):
      self.CreateUser("approver1")
      self.CreateUser("approver2")

    cron_manager = cronjobs.CronManager()
    cron_args = rdf_cronjobs.CreateCronJobArgs(
        frequency="1d",
        allow_overruns=False,
        flow_name=discovery.Interrogate.__name__,
    )
    cron_id = cron_manager.CreateJob(cron_args=cron_args)

    def ReplaceCronAndApprovalIds():
      approvals = self.ListCronJobApprovals()
      return {approvals[0].id: "approval:112233", cron_id: "CronJob_123456"}

    with test_lib.FakeTime(126):
      self.Check(
          "CreateCronJobApproval",
          args=api_user_pb2.ApiCreateCronJobApprovalArgs(
              cron_job_id=cron_id,
              approval=api_user_pb2.ApiCronJobApproval(
                  reason="really important reason!",
                  notified_users=["approver1", "approver2"],
                  email_cc_addresses=["test@example.com"],
              ),
          ),
          replace=ReplaceCronAndApprovalIds,
      )


class ApiGetOwnGrrUserHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest
):
  """Regression test for ApiGetUserSettingsHandler."""

  api_method = "GetGrrUser"
  handler = user_plugin.ApiGetOwnGrrUserHandler

  def Run(self):
    data_store.REL_DB.WriteGRRUser(
        username=self.test_username,
        ui_mode=user_pb2.GUISettings.UIMode.ADVANCED,
        canary_mode=True,
    )

    self.Check("GetGrrUser")

    # Make user an admin and do yet another request.
    data_store.REL_DB.WriteGRRUser(
        username=self.test_username,
        user_type=rdf_objects.GRRUser.UserType.USER_TYPE_ADMIN,
    )

    self.Check("GetGrrUser")


def _SendNotifications(username, client_id):
  with test_lib.FakeTime(42):
    notification.Notify(
        username,
        objects_pb2.UserNotification.Type.TYPE_CLIENT_INTERROGATED,
        "<some message>",
        objects_pb2.ObjectReference(
            reference_type=objects_pb2.ObjectReference.Type.CLIENT,
            client=objects_pb2.ClientReference(client_id=client_id),
        ),
    )

  with test_lib.FakeTime(44):
    notification.Notify(
        username,
        objects_pb2.UserNotification.Type.TYPE_VFS_FILE_COLLECTION_FAILED,
        "<some other message>",
        objects_pb2.ObjectReference(
            reference_type=objects_pb2.ObjectReference.Type.VFS_FILE,
            vfs_file=objects_pb2.VfsFileReference(
                client_id=client_id,
                path_type=objects_pb2.PathInfo.PathType.OS,
                path_components=["foo"],
            ),
        ),
    )


class ApiGetPendingUserNotificationsCountHandlerRegressionTest(
    acl_test_lib.AclTestMixin, api_regression_test_lib.ApiRegressionTest
):
  """Regression test for ApiGetPendingUserNotificationsCountHandler."""

  api_method = "GetPendingUserNotificationsCount"
  handler = user_plugin.ApiGetPendingUserNotificationsCountHandler

  def Run(self):
    client_id = self.SetupClient(0)
    self.CreateUser(self.test_username)
    _SendNotifications(self.test_username, client_id)

    self.Check("GetPendingUserNotificationsCount")


class ApiListPendingUserNotificationsHandlerRegressionTest(
    acl_test_lib.AclTestMixin, api_regression_test_lib.ApiRegressionTest
):
  """Regression test for ApiListPendingUserNotificationsHandler."""

  api_method = "ListPendingUserNotifications"
  handler = user_plugin.ApiListPendingUserNotificationsHandler

  def Run(self):
    client_id = self.SetupClient(0)
    self.CreateUser(self.test_username)

    _SendNotifications(self.test_username, client_id)

    self.Check(
        "ListPendingUserNotifications",
        args=api_user_pb2.ApiListPendingUserNotificationsArgs(),
    )
    self.Check(
        "ListPendingUserNotifications",
        args=api_user_pb2.ApiListPendingUserNotificationsArgs(
            timestamp=43000000
        ),
    )
    self.Check(
        "ListPendingUserNotifications",
        args=api_user_pb2.ApiListPendingUserNotificationsArgs(
            timestamp=44000000
        ),
    )


class ApiListAndResetUserNotificationsHandlerRegressionTest(
    acl_test_lib.AclTestMixin, api_regression_test_lib.ApiRegressionTest
):
  """Regression test for ApiListAndResetUserNotificationsHandler."""

  api_method = "ListAndResetUserNotifications"
  handler = user_plugin.ApiListAndResetUserNotificationsHandler

  def Run(self):
    client_id = self.SetupClient(0)
    self.CreateUser(self.test_username)
    _SendNotifications(self.test_username, client_id)

    # _SendNotifications schedule notifications at timestamp 42 and 44.
    # REL_DB-based ListAndResetUserNotifications implementation only
    # reads last 6 months worth of notifications. Hence - using FakeTime.
    with test_lib.FakeTime(45):
      # Notifications are pending in this request.
      self.Check(
          "ListAndResetUserNotifications",
          args=api_user_pb2.ApiListAndResetUserNotificationsArgs(),
      )

      # But not anymore in these requests.
      self.Check(
          "ListAndResetUserNotifications",
          args=api_user_pb2.ApiListAndResetUserNotificationsArgs(
              offset=1, count=1
          ),
      )
      self.Check(
          "ListAndResetUserNotifications",
          args=api_user_pb2.ApiListAndResetUserNotificationsArgs(
              filter="other"
          ),
      )


class ApiListApproverSuggestionsHandlerRegressionTest(
    acl_test_lib.AclTestMixin, api_regression_test_lib.ApiRegressionTest
):
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
        args=api_user_pb2.ApiListApproverSuggestionsArgs(username_query="foo"),
    )

    # Check formatting of multiple suggestions.
    self.Check(
        "ListApproverSuggestions",
        args=api_user_pb2.ApiListApproverSuggestionsArgs(
            username_query="sanchez"
        ),
    )


def main(argv):
  api_regression_test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
