#!/usr/bin/env python
"""Tests for GRR settings-related views."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


from grr_response_core.lib import flags
from grr_response_server.gui import gui_test_lib
from grr_response_server.gui.api_plugins import config_test as api_config_test
from grr.test_lib import db_test_lib
from grr.test_lib import test_lib


@db_test_lib.DualDBTest
class TestSettingsView(gui_test_lib.GRRSeleniumTest):
  """Test the settings GUI."""

  def testSettingsView(self):
    with test_lib.ConfigOverrider({
        "ACL.group_access_manager_class": "Foo bar.",
        "AdminUI.bind": "127.0.0.1"
    }):
      self.Open("/#/config")

      self.WaitUntil(self.IsTextPresent, "Configuration")

      # Check that configuration values are displayed.
      self.WaitUntil(self.IsTextPresent, "ACL.group_access_manager_class")
      self.WaitUntil(self.IsTextPresent, "Foo bar.")

      self.WaitUntil(self.IsTextPresent, "AdminUI.bind")
      self.WaitUntil(self.IsTextPresent, "127.0.0.1")


@db_test_lib.DualDBTest
class TestManageBinariesView(gui_test_lib.GRRSeleniumTest,
                             api_config_test.ApiGrrBinaryTestMixin):
  """Test the Manage Binaries GUI."""

  def setUp(self):
    super(TestManageBinariesView, self).setUp()
    self.SetUpBinaries()

  def testNotAccessibleForNonAdmins(self):
    self.Open("/")

    self.WaitUntil(
        self.IsElementPresent,
        "css=li[grr-nav-link]:contains('Manage Binaries') i.fa-lock")

  def testEachBinaryIsCorrectlyShown(self):
    self.CreateAdminUser(u"gui_user")

    self.Open("/#/manage-binaries")

    self.WaitUntil(self.IsElementPresent,
                   "css=li[grr-nav-link]:contains('Manage Binaries')")
    self.WaitUntilNot(
        self.IsElementPresent,
        "css=li[grr-nav-link]:contains('Manage Binaries') i.fa-lock")

    self.WaitUntil(
        self.IsElementPresent, "css=grr-config-binaries-view "
        "div.panel:contains('Python Hacks') tr:contains('test')")
    self.WaitUntil(
        self.IsElementPresent, "css=grr-config-binaries-view "
        "div.panel:contains('Python Hacks') tr:contains('17B')")
    self.WaitUntil(
        self.IsElementPresent, "css=grr-config-binaries-view "
        "div.panel:contains('Python Hacks') "
        "tr:contains('1970-01-01 00:00:43 UTC')")

    self.WaitUntil(
        self.IsElementPresent, "css=grr-config-binaries-view "
        "div.panel:contains('Executables') tr:contains('test.exe')")
    self.WaitUntil(
        self.IsElementPresent, "css=grr-config-binaries-view "
        "div.panel:contains('Executables') tr:contains('18B')")
    self.WaitUntil(
        self.IsElementPresent, "css=grr-config-binaries-view "
        "div.panel:contains('Executables') "
        "tr:contains('1970-01-01 00:00:42 UTC')")


if __name__ == "__main__":
  flags.StartMain(test_lib.main)
