#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Test the GUI host information."""


from grr.gui import gui_test_lib
from grr.gui import runtests_test

from grr.lib import action_mocks
from grr.lib import aff4
from grr.lib import flags
from grr.lib import test_lib
from grr.lib.rdfvalues import client as rdf_client


class TestHostInformation(gui_test_lib.GRRSeleniumTest):
  """Test the host information interface."""

  def setUp(self):
    super(TestHostInformation, self).setUp()
    self.client_id = "C.0000000000000001"

    test_lib.ClientFixture(self.client_id, token=self.token)
    self.RequestAndGrantClientApproval(self.client_id)

    with test_lib.FakeTime(gui_test_lib.TIME_0):
      with aff4.FACTORY.Open(self.client_id, mode="rw", token=self.token) as fd:
        fd.Set(fd.Schema.OS_VERSION, rdf_client.VersionString("6.1.7000"))
        fd.Set(fd.Schema.HOSTNAME("Hostname T0"))
        fd.Set(fd.Schema.MEMORY_SIZE(4294967296))

    with test_lib.FakeTime(gui_test_lib.TIME_1):
      with aff4.FACTORY.Open(self.client_id, mode="rw", token=self.token) as fd:
        fd.Set(fd.Schema.OS_VERSION, rdf_client.VersionString("6.1.8000"))
        fd.Set(fd.Schema.HOSTNAME("Hostname T1"))
        fd.Set(fd.Schema.MEMORY_SIZE(8589934592))

    with test_lib.FakeTime(gui_test_lib.TIME_2):
      with aff4.FACTORY.Open(self.client_id, mode="rw", token=self.token) as fd:
        fd.Set(fd.Schema.OS_VERSION, rdf_client.VersionString("7.0.0000"))
        fd.Set(fd.Schema.HOSTNAME("Hostname T2"))
        fd.Set(fd.Schema.MEMORY_SIZE(12884901888))

  def testClickingOnInterrogateStartsInterrogateFlow(self):
    self.Open("/#c=" + self.client_id)

    # A click on the Interrogate button starts a flow, disables the button and
    # shows a loading icon within the button.
    self.Click("css=button:contains('Interrogate'):not([disabled])")
    self.WaitUntil(self.IsElementPresent,
                   "css=button:contains('Interrogate')[disabled]")
    self.WaitUntil(self.IsElementPresent,
                   "css=button:contains('Interrogate') i")

    # Get the started flow and finish it, this will re-enable the button.
    client_id = rdf_client.ClientURN(self.client_id)

    fd = aff4.FACTORY.Open(client_id.Add("flows"), token=self.token)
    flows = list(fd.ListChildren())

    client_mock = action_mocks.ActionMock()
    for flow_urn in flows:
      for _ in test_lib.TestFlowHelper(
          flow_urn,
          client_mock,
          client_id=client_id,
          token=self.token,
          check_flow_errors=False):
        pass

    self.WaitUntilNot(self.IsElementPresent,
                      "css=button:contains('Interrogate')[disabled]")

    # Check if an Interrogate flow was started.
    self.Click("css=a[grrtarget='client.flows']")
    self.Click("css=td:contains('Interrogate')")
    self.WaitUntilContains("Interrogate", self.GetText,
                           "css=table td.proto_key:contains('Flow name') "
                           "~ td.proto_value")

  def testChangingVersionDropdownChangesClientInformation(self):
    self.Open("/#c=" + self.client_id)

    # Check that the newest version is selected.
    self.WaitUntilContains(
        gui_test_lib.DateString(gui_test_lib.TIME_2), self.GetText,
        "css=.version-dropdown > option[selected]")
    self.WaitUntil(self.IsTextPresent, "Hostname T2")
    self.WaitUntil(self.IsTextPresent, "12Gb")

    self.Click("css=select.version-dropdown > option:contains(\"%s\")" %
               gui_test_lib.DateString(gui_test_lib.TIME_1))
    self.WaitUntil(self.IsTextPresent, "Hostname T1")
    self.WaitUntil(self.IsTextPresent, "6.1.8000")
    self.WaitUntil(self.IsTextPresent, "8Gb")
    self.WaitUntil(self.IsTextPresent, "Newer Version available")

    # Also the details show the selected version.
    self.Click("css=label:contains('Full details')")
    self.WaitUntil(self.IsTextPresent, "Hostname T1")
    self.WaitUntil(self.IsTextPresent, "6.1.8000")
    self.WaitUntil(self.IsTextPresent, "8Gb")

    # Check that changing the version does not change the view, i.e. that
    # we are still in the full details view.
    self.Click("css=select.version-dropdown > option:contains(\"%s\")" %
               gui_test_lib.DateString(gui_test_lib.TIME_0))
    self.WaitUntil(self.IsTextPresent, "Hostname T0")
    self.WaitUntil(self.IsTextPresent, "6.1.7000")
    self.WaitUntil(self.IsTextPresent, "4Gb")


def main(argv):
  # Run the full test suite
  runtests_test.SeleniumTestProgram(argv=argv)


if __name__ == "__main__":
  flags.StartMain(main)
