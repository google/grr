#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Test the GUI host information."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


from grr_response_core.lib import flags

from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import config as rdf_config
from grr_response_server import aff4
from grr_response_server import data_store
from grr_response_server.flows.general import discovery
from grr_response_server.gui import gui_test_lib
from grr.test_lib import db_test_lib
from grr.test_lib import fixture_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib


@db_test_lib.DualDBTest
class TestHostInformation(gui_test_lib.GRRSeleniumTest):
  """Test the host information interface."""

  def _WriteClientSnapshot(self, timestamp, version, hostname, memory):
    with test_lib.FakeTime(timestamp):
      with aff4.FACTORY.Open(self.client_id, mode="rw", token=self.token) as fd:
        fd.Set(fd.Schema.OS_VERSION, rdf_client.VersionString(version))
        fd.Set(fd.Schema.HOSTNAME(hostname))
        fd.Set(fd.Schema.MEMORY_SIZE(memory))

    if data_store.RelationalDBReadEnabled():
      snapshot = data_store.REL_DB.ReadClientSnapshot(self.client_id)
      with test_lib.FakeTime(timestamp):
        snapshot.os_version = version
        snapshot.knowledge_base.fqdn = hostname
        snapshot.memory_size = memory
        data_store.REL_DB.WriteClientSnapshot(snapshot)

  def setUp(self):
    super(TestHostInformation, self).setUp()
    self.client_id = u"C.0000000000000001"

    fixture_test_lib.ClientFixture(self.client_id, token=self.token)
    self.RequestAndGrantClientApproval(self.client_id)

    self._WriteClientSnapshot(gui_test_lib.TIME_0, "6.1.7000", "Hostname T0",
                              4294967296)
    self._WriteClientSnapshot(gui_test_lib.TIME_1, "6.1.8000", "Hostname T1",
                              8589934592)
    self._WriteClientSnapshot(gui_test_lib.TIME_2, "7.0.0000", "Hostname T2",
                              12884901888)

  def testClickingOnInterrogateStartsInterrogateFlow(self):
    self.Open("/#/clients/%s" % self.client_id)

    # A click on the Interrogate button starts a flow, disables the button and
    # shows a loading icon within the button.
    self.Click("css=button:contains('Interrogate'):not([disabled])")
    self.WaitUntil(self.IsElementPresent,
                   "css=button:contains('Interrogate')[disabled]")
    self.WaitUntil(self.IsElementPresent,
                   "css=button:contains('Interrogate') i")

    # Get the started flow and finish it, this will re-enable the button.
    flow_test_lib.FinishAllFlowsOnClient(
        self.client_id, check_flow_errors=False)

    self.WaitUntilNot(self.IsElementPresent,
                      "css=button:contains('Interrogate')[disabled]")

    # Check if an Interrogate flow was started.
    self.Click("css=a[grrtarget='client.flows']")
    self.Click("css=td:contains('Interrogate')")
    self.WaitUntilContains(
        discovery.Interrogate.__name__, self.GetText,
        "css=table td.proto_key:contains('Flow name') "
        "~ td.proto_value")

  def testChangingVersionDropdownChangesClientInformation(self):
    self.Open("/#/clients/%s" % self.client_id)

    # Check that the newest version is selected.
    self.WaitUntilContains(
        gui_test_lib.DateString(gui_test_lib.TIME_2), self.GetText,
        "css=.version-dropdown > option[selected]")
    self.WaitUntil(self.IsTextPresent, "Hostname T2")
    self.WaitUntil(self.IsTextPresent, "12GiB")

    self.Click("css=select.version-dropdown > option:contains(\"%s\")" %
               gui_test_lib.DateString(gui_test_lib.TIME_1))
    self.WaitUntil(self.IsTextPresent, "Hostname T1")
    self.WaitUntil(self.IsTextPresent, "6.1.8000")
    self.WaitUntil(self.IsTextPresent, "8GiB")
    self.WaitUntil(self.IsTextPresent, "Newer Version available")

    # Also the details show the selected version.
    self.Click("css=label:contains('Full details')")
    self.WaitUntil(self.IsTextPresent, "Hostname T1")
    self.WaitUntil(self.IsTextPresent, "6.1.8000")
    self.WaitUntil(self.IsTextPresent, "8GiB")

    # Check that changing the version does not change the view, i.e. that
    # we are still in the full details view.
    self.Click("css=select.version-dropdown > option:contains(\"%s\")" %
               gui_test_lib.DateString(gui_test_lib.TIME_0))
    self.WaitUntil(self.IsTextPresent, "Hostname T0")
    self.WaitUntil(self.IsTextPresent, "6.1.7000")
    self.WaitUntil(self.IsTextPresent, "4GiB")

  def testClickingOnHistoryButtonOpensAttributeHistoryDialog(self):
    self.Open("/#/clients/" + self.client_id)

    # Wait until client information appears and click on 'Full details' button.
    self.WaitUntil(self.IsTextPresent, "Hostname T2")
    self.Click("css=label:contains('Full details')")

    self.MoveMouseTo("css=tr:contains('Os info') tr:contains('Fqdn') "
                     "td.proto_key")
    self.Click("css=tr:contains('Os info') tr:contains('Fqdn') "
               ".proto_history button")

    self.WaitUntil(self.IsElementPresent,
                   "css=h4:contains('os_info.fqdn history')")
    # Check that hostnames are listed in the right order.
    self.WaitUntil(
        self.IsElementPresent, "css=tr:contains('Hostname T2') ~ "
        "tr:contains('Hostname T1') ~ "
        "tr:contains('Hostname T0')")

    # Check that the dialog is successfully closed.
    self.Click(
        "css=grr-host-history-dialog .modal-footer button:contains('Close')")
    self.WaitUntilNot(self.IsElementPresent,
                      "css=h4:contains('os_info.node history')")

  WARNINGS_OPTION = rdf_config.AdminUIClientWarningsConfigOption(rules=[
      rdf_config.AdminUIClientWarningRule(
          with_labels=["blah"], message="*a big warning message*")
  ])

  def testSidebarWarningIsNotShownIfClientHasNoLabels(self):
    with test_lib.ConfigOverrider({
        "AdminUI.client_warnings": self.WARNINGS_OPTION
    }):
      self.Open("/#/clients/" + self.client_id)

      self.WaitUntil(self.IsElementPresent,
                     "css=grr-client-summary:contains('Hostname T2')")
      self.WaitUntilNot(self.IsElementPresent,
                        "css=div.danger em:contains('a big warning message')")

  def testSidebarWarningIsNotShownIfClientHasNonMatchingLabels(self):
    self.AddClientLabel(self.client_id, self.token.username, u"another")

    with test_lib.ConfigOverrider({
        "AdminUI.client_warnings": self.WARNINGS_OPTION
    }):
      self.Open("/#/clients/" + self.client_id)

      self.WaitUntil(self.IsElementPresent,
                     "css=grr-client-summary:contains('Hostname T2')")
      self.WaitUntilNot(self.IsElementPresent,
                        "css=div.danger em:contains('a big warning message')")

  def testSidebarWarningIsShownIfClientMatchesLabels(self):
    self.AddClientLabel(self.client_id, self.token.username, u"blah")

    with test_lib.ConfigOverrider({
        "AdminUI.client_warnings": self.WARNINGS_OPTION
    }):
      self.Open("/#/clients/" + self.client_id)

      self.WaitUntil(
          self.IsElementPresent,
          "css=div.alert-danger em:contains('a big warning message')")


if __name__ == "__main__":
  flags.StartMain(test_lib.main)
