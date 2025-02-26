#!/usr/bin/env python
"""Tests for GRR settings-related views."""

from absl import app

from grr_response_core.lib.rdfvalues import config as rdf_config
from grr_response_server.gui import gui_test_lib
from grr_response_server.gui.api_plugins import config_test as api_config_test
from grr.test_lib import test_lib


class TestSettingsView(gui_test_lib.GRRSeleniumTest):
  """Test the settings GUI."""

  def testSettingsView(self):
    with test_lib.ConfigOverrider({
        "ACL.group_access_manager_class": "Foo bar.",
        "AdminUI.bind": "127.0.0.1",
        "AdminUI.hunt_config": rdf_config.AdminUIHuntConfig(
            default_exclude_labels=["oh-oh"],
        ),
        "Source.version_major": 42,
        "Hunt.default_client_rate": 42.0,
        "Email.enable_custom_email_address": True,
        "Cron.disabled_cron_jobs": ["Job1", "Job2"],
        "Server.fleetspeak_last_ping_threshold": "1h",
        "Server.raw_filesystem_access_pathtype": "TSK",
        "ClientBuilder.build_type": "Debug",
        "ClientBuilder.target_platforms": [
            "darwin_amd64_dmg",
            "linux_amd64_deb",
        ],
        "ClientRepacker.output_filename": (
            "%(ClientRepacker.output_basename)%(ClientBuilder.output_extension)"
        ),
        "Mysql.password": "top-secret",
    }):
      self.Open("/legacy#/config")

      self.WaitUntil(self.IsTextPresent, "Configuration")

      # Check that configuration values are displayed.
      self.WaitUntil(
          self.IsElementPresent,
          "css=tr:contains('ACL.group_access_manager_class') :contains('Foo"
          " bar.')",
      )
      self.WaitUntil(
          self.IsElementPresent,
          "css=tr:contains('AdminUI.bind') :contains('127.0.0.1')",
      )
      self.WaitUntil(
          self.IsElementPresent,
          "css=tr:contains('PrivateKeys.executable_signing_private_key')"
          " :contains('(redacted)')",
      )
      # AdminUI.hunt_config is an RDFProtoStruct.
      self.WaitUntil(
          self.IsElementPresent,
          "css=tr:contains('AdminUI.hunt_config') tr:contains('Default exclude"
          " labels') :contains('oh-oh')",
      )
      # Source.version_major is an int field.
      self.WaitUntil(
          self.IsElementPresent,
          "css=tr:contains('Source.version_major') :contains('42')",
      )
      # Hunt.default_client_rate is a float field, displayed as an int.
      self.WaitUntil(
          self.IsElementPresent,
          "css=tr:contains('Hunt.default_client_rate') :contains('42')",
      )
      # Email.enable_custom_email_address is a boolean field.
      self.WaitUntil(
          self.IsElementPresent,
          "css=tr:contains('Email.enable_custom_email_address')"
          " :contains('true')",
      )
      # Cron.disabled_cron_jobs is a list (unsupported).
      self.WaitUntil(
          self.IsElementPresent,
          "css=tr:contains('Cron.disabled_cron_jobs'):not(:contains('Job1,"
          " Job2'))",
      )
      # Server.fleetspeak_last_ping_threshold is an RDF Duration.
      self.WaitUntil(
          self.IsElementPresent,
          "css=tr:contains('Server.fleetspeak_last_ping_threshold')"
          " :contains('3600000000')",
      )
      # Server.raw_filesystem_access_pathtype is an enum.
      self.WaitUntil(
          self.IsElementPresent,
          "css=tr:contains('Server.raw_filesystem_access_pathtype')"
          " :contains('TSK')",
      )
      # ClientBuilder.build_type is a "choice".
      self.WaitUntil(
          self.IsElementPresent,
          "css=tr:contains('ClientBuilder.build_type') :contains('Debug')",
      )
      # ClientBuilder.target_platforms is a "multi-choice" (unsupported).
      self.WaitUntil(
          self.IsElementPresent,
          "css=tr:contains('ClientBuilder.target_platforms'):not(:contains('darwin_amd64_dmg,"
          " linux_amd64_deb'))",
      )
      # ClientRepacker.output_filename is an "option".
      self.WaitUntil(
          self.IsElementPresent,
          "css=tr:contains('ClientRepacker.output_filename')"
          " :contains('GRR_0.0.0.0_')",
      )
      # Mysql.password should be redacted.
      self.WaitUntil(
          self.IsElementPresent,
          "css=tr:contains('Mysql.password'):not(:contains('top-secret'))"
          " :contains(redacted)",
      )


class TestManageBinariesView(
    gui_test_lib.GRRSeleniumTest, api_config_test.ApiGrrBinaryTestMixin
):
  """Test the Binaries GUI."""

  def setUp(self):
    super().setUp()
    self.SetUpBinaries()

  def testNotAccessibleForNonAdmins(self):
    self.Open("/legacy")

    self.WaitUntil(
        self.IsElementPresent,
        "css=li[grr-nav-link]:contains('Binaries') i.fa-lock",
    )

  def testEachBinaryIsCorrectlyShown(self):
    self.CreateAdminUser("gui_user")

    self.Open("/legacy#/manage-binaries")

    self.WaitUntil(
        self.IsElementPresent, "css=li[grr-nav-link]:contains('Binaries')"
    )
    self.WaitUntilNot(
        self.IsElementPresent,
        "css=li[grr-nav-link]:contains('Binaries') i.fa-lock",
    )

    self.WaitUntil(
        self.IsElementPresent,
        "css=grr-config-binaries-view "
        "div.panel:contains('Python Hacks') tr:contains('test')",
    )
    self.WaitUntil(
        self.IsElementPresent,
        "css=grr-config-binaries-view "
        "div.panel:contains('Python Hacks') tr:contains('17B')",
    )
    self.WaitUntil(
        self.IsElementPresent,
        "css=grr-config-binaries-view "
        "div.panel:contains('Python Hacks') "
        "tr:contains('1970-01-01 00:00:43 UTC')",
    )

    self.WaitUntil(
        self.IsElementPresent,
        "css=grr-config-binaries-view "
        "div.panel:contains('Executables') tr:contains('test.exe')",
    )
    self.WaitUntil(
        self.IsElementPresent,
        "css=grr-config-binaries-view "
        "div.panel:contains('Executables') tr:contains('18B')",
    )
    self.WaitUntil(
        self.IsElementPresent,
        "css=grr-config-binaries-view "
        "div.panel:contains('Executables') "
        "tr:contains('1970-01-01 00:00:42 UTC')",
    )


if __name__ == "__main__":
  app.run(test_lib.main)
