#!/usr/bin/env python
"""This module contains tests for user API renderers."""



from grr.gui import api_test_lib
from grr.gui.api_plugins import user as user_plugin

from grr.lib import access_control
from grr.lib import aff4
from grr.lib import flags
from grr.lib import flow
from grr.lib import hunts
from grr.lib import test_lib
from grr.lib import utils

from grr.lib.aff4_objects import users as aff4_users


class ApiUserApprovalsListRendererTest(test_lib.GRRBaseTest):
  """Test for ApiUserApprovalsListRenderer."""

  def setUp(self):
    super(ApiUserApprovalsListRendererTest, self).setUp()
    self.client_id = self.SetupClients(1)[0]
    self.renderer = user_plugin.ApiUserApprovalsListRenderer()

  def testRendersRequestedClientApproval(self):
    flow.GRRFlow.StartFlow(client_id=self.client_id,
                           flow_name="RequestClientApprovalFlow",
                           reason=self.token.reason,
                           subject_urn=self.client_id,
                           approver="approver",
                           token=self.token)

    args = user_plugin.ApiUserApprovalsListRendererArgs(approval_type="client")
    result = self.renderer.Render(args, token=self.token)

    self.assertEqual(result["offset"], 0)
    self.assertEqual(result["count"], 1)
    self.assertEqual(len(result["items"]), 1)

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

    args = user_plugin.ApiUserApprovalsListRendererArgs(approval_type="hunt")
    result = self.renderer.Render(args, token=self.token)

    self.assertEqual(result["offset"], 0)
    self.assertEqual(result["count"], 1)
    self.assertEqual(len(result["items"]), 1)

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

    args = user_plugin.ApiUserApprovalsListRendererArgs(approval_type="cron")
    result = self.renderer.Render(args, token=self.token)

    self.assertEqual(result["offset"], 0)
    self.assertEqual(result["count"], 1)
    self.assertEqual(len(result["items"]), 1)


class ApiUserApprovalsListRendererRegressionTest(
    api_test_lib.ApiCallRendererRegressionTest):
  """Regression test for ApiUserApprovalsListRendererTest."""

  renderer = "ApiUserApprovalsListRenderer"

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

      hunt = hunts.GRRHunt.StartHunt(
          hunt_name="GenericHunt", token=self.token)

    with test_lib.FakeTime(43):
      flow.GRRFlow.StartFlow(flow_name="RequestHuntApprovalFlow",
                             reason=self.token.reason,
                             subject_urn=hunt.urn,
                             approver="approver",
                             token=self.token)

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
      self.Check("GET", "/api/users/me/approvals/hunt",
                 replace={utils.SmartStr(hunt.urn.Basename()): "H:123456"})


class ApiUserSettingsRendererTest(test_lib.GRRBaseTest):
  """Test for ApiUserSettingsRenderer."""

  def setUp(self):
    super(ApiUserSettingsRendererTest, self).setUp()
    self.renderer = user_plugin.ApiUserSettingsRenderer()

  def testRendersSettingsForUserCorrespondingToToken(self):
    with aff4.FACTORY.Create(
        aff4.ROOT_URN.Add("users").Add("foo"),
        aff4_type="GRRUser", mode="w", token=self.token) as user_fd:
      user_fd.Set(user_fd.Schema.GUI_SETTINGS,
                  aff4_users.GUISettings(mode="ADVANCED",
                                         canary_mode=True,
                                         docs_location="REMOTE"))

    result = self.renderer.Render(None,
                                  token=access_control.ACLToken(username="foo"))
    self.assertEqual(result["value"]["mode"]["value"], "ADVANCED")
    self.assertEqual(result["value"]["canary_mode"]["value"], True)
    self.assertEqual(result["value"]["docs_location"]["value"], "REMOTE")


class ApiUserSettingsRendererRegresstionTest(
    api_test_lib.ApiCallRendererRegressionTest):
  """Regression test for ApiUserSettingsRenderer."""

  renderer = "ApiUserSettingsRenderer"

  def Run(self):
    with test_lib.FakeTime(42):
      with aff4.FACTORY.Create(
          aff4.ROOT_URN.Add("users").Add(self.token.username),
          aff4_type="GRRUser", mode="w", token=self.token) as user_fd:
        user_fd.Set(user_fd.Schema.GUI_SETTINGS,
                    aff4_users.GUISettings(canary_mode=True))

    self.Check("GET", "/api/users/me/settings")


class ApiSetUserSettingsRendererTest(test_lib.GRRBaseTest):
  """Tests for ApiSetUserSettingsRenderer."""

  def setUp(self):
    super(ApiSetUserSettingsRendererTest, self).setUp()
    self.renderer = user_plugin.ApiSetUserSettingsRenderer()

  def testSetsSettingsForUserCorrespondingToToken(self):
    settings = aff4_users.GUISettings(mode="ADVANCED",
                                      canary_mode=True,
                                      docs_location="REMOTE")

    # Render the request - effectively applying the settings for user "foo".
    result = self.renderer.Render(settings,
                                  token=access_control.ACLToken(username="foo"))
    self.assertEqual(result["status"], "OK")

    # Check that settings for user "foo" were applied.
    fd = aff4.FACTORY.Open("aff4:/users/foo", token=self.token)
    self.assertEqual(fd.Get(fd.Schema.GUI_SETTINGS), settings)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
