#!/usr/bin/env python
"""This module contains tests for user API renderers."""



# pylint: disable=unused-import,g-bad-import-order
from grr.lib import server_plugins
# pylint: enable=unused-import,g-bad-import-order

from grr.gui import api_test_lib
from grr.gui.api_plugins import user as user_plugin

from grr.lib import aff4
from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import test_lib


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
                  rdfvalue.GUISettings(mode="ADVANCED",
                                       canary_mode=True,
                                       docs_location="REMOTE"))

    result = self.renderer.Render(None, token=rdfvalue.ACLToken(username="foo"))
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
                    rdfvalue.GUISettings(canary_mode=True))

    self.Check("GET", "/api/users/me/settings")


class ApiSetUserSettingsRendererTest(test_lib.GRRBaseTest):
  """Tests for ApiSetUserSettingsRenderer."""

  def setUp(self):
    super(ApiSetUserSettingsRendererTest, self).setUp()
    self.renderer = user_plugin.ApiSetUserSettingsRenderer()

  def testSetsSettingsForUserCorrespondingToToken(self):
    settings = rdfvalue.GUISettings(mode="ADVANCED",
                                    canary_mode=True,
                                    docs_location="REMOTE")

    # Render the request - effectively applying the settings for user "foo".
    result = self.renderer.Render(settings,
                                  token=rdfvalue.ACLToken(username="foo"))
    self.assertEqual(result["status"], "OK")

    # Check that settings for user "foo" were applied.
    fd = aff4.FACTORY.Open("aff4:/users/foo", token=self.token)
    self.assertEqual(fd.Get(fd.Schema.GUI_SETTINGS), settings)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
