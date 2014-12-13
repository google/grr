#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

"""Test the statistics viewer."""


from grr.gui import runtests_test

from grr.lib import access_control
from grr.lib import aff4
from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import test_lib


class TestStats(test_lib.GRRSeleniumTest):
  """Test the statistics interface."""

  @staticmethod
  def PopulateData():
    """Populates data into the stats object."""
    token = access_control.ACLToken(username="test", reason="fixture")

    with aff4.FACTORY.Create(
        "aff4:/stats/ClientFleetStats", "ClientFleetStats", token=token) as fd:
      now = 1321057655

      for i in range(10, 15):
        histogram = fd.Schema.OS_HISTOGRAM(
            age=int((now + i * 60 * 60 * 24) * 1e6))

        for number in [1, 7, 14, 30]:
          graph = rdfvalue.Graph(title="%s day actives" % number)
          graph.Append(label="Windows", y_value=i + number)
          graph.Append(label="Linux", y_value=i * 2 + number)

          histogram.Append(graph)

        fd.AddAttribute(histogram)

  def testStats(self):
    """Test the statistics interface.

    Unfortunately this test is pretty lame because we can not look into the
    canvas object with selenium.
    """
    self.Open("/")

    self.WaitUntil(self.IsElementPresent, "client_query")

    # Make sure the foreman is not there (we are not admin yet)
    self.assert_(not self.IsElementPresent(
        "css=a[grrtarget=ReadOnlyForemanRuleTable]"))

    # Make "test" user an admin
    with self.ACLChecksDisabled():
      self.CreateAdminUser("test")

    self.Open("/")

    self.WaitUntil(self.IsElementPresent, "client_query")

    # Make sure that now we can see this option.
    self.WaitUntil(self.IsElementPresent,
                   "css=a[grrtarget=ReadOnlyForemanRuleTable]")

    # Go to Statistics
    self.Click("css=a:contains('Statistics')")

    self.Click("css=#_Clients ins.jstree-icon")

    self.Click("css=#_Clients-OS_20Breakdown ins.jstree-icon")

    self.WaitUntil(self.IsElementPresent,
                   "css=#_Clients-OS_20Breakdown-_207_20Day_20Active")
    self.Click("css=li[path='/Clients/OS Breakdown/ 7 Day Active'] a")

    self.WaitUntilEqual(u"No data Available",
                        self.GetText, "css=#main_rightPane h3")

    with self.ACLChecksDisabled():
      self.PopulateData()

    self.Click("css=li[path='/Clients/OS Breakdown/ 7 Day Active'] a")

    self.WaitUntilEqual(u"Operating system break down.",
                        self.GetText, "css=#main_rightPane h3")


def main(argv):
  # Run the full test suite
  runtests_test.SeleniumTestProgram(argv=argv)

if __name__ == "__main__":
  flags.StartMain(main)
