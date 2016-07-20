#!/usr/bin/env python
from grr.gui import runtests_test
from grr.lib import flags
from grr.lib import test_lib


class TestSettingsView(test_lib.GRRSeleniumTest):
  """Test the settings GUI."""

  def setUp(self):
    super(TestSettingsView, self).setUp()

  def tearDown(self):
    super(TestSettingsView, self).tearDown()

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


def main(argv):
  # Run the full test suite
  runtests_test.SeleniumTestProgram(argv=argv)


if __name__ == "__main__":
  flags.StartMain(main)
