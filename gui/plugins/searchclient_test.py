#!/usr/bin/env python
"""Tests for the main content view."""


from grr.gui import runtests_test

# We have to import test_lib first to properly initialize aff4 and rdfvalues.
# pylint: disable=g-bad-import-order
from grr.lib import test_lib
# pylint: enable=g-bad-import-order

from grr.lib import aff4
from grr.lib import flags
from grr.lib import rdfvalue


class TestNavigatorView(test_lib.GRRSeleniumTest):
  """Tests for NavigatorView (left side bar)."""

  def CreateClient(self, last_ping=None):
    if last_ping is None:
      raise ValueError("last_ping can't be None")

    with self.ACLChecksDisabled():
      client_id = self.SetupClients(1)[0]
      with aff4.FACTORY.Open(
          client_id, mode="rw", token=self.token) as client_obj:
        client_obj.Set(client_obj.Schema.PING(last_ping))

      self.GrantClientApproval(client_id)

    client_obj = aff4.FACTORY.Open(client_id, token=self.token)
    return client_id

  def testOnlineClientStatus(self):
    client_id = self.CreateClient(last_ping=rdfvalue.RDFDatetime().Now())
    self.Open("/#c=" + str(client_id))
    self.WaitUntil(self.IsElementPresent, "css=img[src$='online.png']")

  def testOneDayClientStatus(self):
    client_id = self.CreateClient(
        last_ping=rdfvalue.RDFDatetime().Now() - rdfvalue.Duration("1h"))
    self.Open("/#c=" + str(client_id))
    self.WaitUntil(self.IsElementPresent, "css=img[src$='online-1d.png']")

  def testOfflineClientStatus(self):
    client_id = self.CreateClient(
        last_ping=rdfvalue.RDFDatetime().Now() - rdfvalue.Duration("1d"))
    self.Open("/#c=" + str(client_id))
    self.WaitUntil(self.IsElementPresent, "css=img[src$='offline.png']")


class TestContentView(test_lib.GRRSeleniumTest):
  """Tests the main content view."""

  def testRendererShowsCanaryContentWhenInCanaryMode(self):
    with self.ACLChecksDisabled():
      with aff4.FACTORY.Create("aff4:/users/test", "GRRUser",
                               token=self.token) as user:
        user.Set(user.Schema.GUI_SETTINGS(canary_mode=True))

    self.Open("/#main=CanaryTestRenderer")
    self.WaitUntil(self.IsTextPresent, "CANARY MODE IS ON")

  def testRendererDoesNotShowCanaryContentWhenNotInCanaryMode(self):
    self.Open("/#main=CanaryTestRenderer")
    self.WaitUntil(self.IsTextPresent, "CANARY MODE IS OFF")

  def testCanaryModeIsAppliedImmediately(self):
    # Canary mode is off by default.
    self.Open("/#main=CanaryTestRenderer")
    self.WaitUntil(self.IsTextPresent, "CANARY MODE IS OFF")

    # Go to the user settings and turn canary mode on.
    self.Click("user_settings_button")
    self.WaitUntil(self.IsTextPresent, "Canary mode")
    self.Click("settings-canary_mode")
    self.Click("css=button[name=Proceed]")

    # Page should get updated and now canary mode should be on.
    self.WaitUntil(self.IsTextPresent, "CANARY MODE IS ON")

    # Go to the user settings and turn canary mode off.
    self.Click("user_settings_button")
    self.WaitUntil(self.IsTextPresent, "Canary mode")
    self.Click("settings-canary_mode")
    self.Click("css=button[name=Proceed]")

    # Page should get updated and now canary mode should be off.
    self.WaitUntil(self.IsTextPresent, "CANARY MODE IS OFF")


def main(argv):
  # Run the full test suite
  runtests_test.SeleniumTestProgram(argv=argv)

if __name__ == "__main__":
  flags.StartMain(main)
