#!/usr/bin/env python
"""Tests for the main content view."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


from grr_response_core.lib import flags
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_server import aff4
from grr_response_server import client_index
from grr_response_server import data_store
from grr_response_server.gui import gui_test_lib
from grr.test_lib import db_test_lib
from grr.test_lib import hunt_test_lib
from grr.test_lib import test_lib


@db_test_lib.DualDBTest
class TestClientSearch(gui_test_lib.SearchClientTestBase,
                       hunt_test_lib.StandardHuntTestMixin):

  def setUp(self):
    super(TestClientSearch, self).setUp()
    self._CreateClients()

  def _CreateClients(self):
    # To test all search keywords, we can rely on SetupClients
    # creating clients with attributes containing a numberic
    # value, e.g. hostname will be Host-0, Host-1, etc.
    self.client_ids = self.SetupClients(15)

    self.AddClientLabel(self.client_ids[0], self.token.username,
                        u"common_test_label")
    self.AddClientLabel(self.client_ids[0], self.token.username,
                        u"unique_test_label")
    self.AddClientLabel(self.client_ids[1], self.token.username,
                        u"common_test_label")

    if data_store.RelationalDBReadEnabled():
      snapshot = data_store.REL_DB.ReadClientSnapshot(
          self.client_ids[0].Basename())
      snapshot.knowledge_base.users.Append(
          rdf_client.User(username="sample_user"))
      snapshot.knowledge_base.users.Append(
          rdf_client.User(username=self.token.username))
      data_store.REL_DB.WriteClientSnapshot(snapshot)
      client_index.ClientIndex().AddClient(
          data_store.REL_DB.ReadClientSnapshot(self.client_ids[0].Basename()))
    else:
      # SetupClients adds no labels or user names.
      with aff4.FACTORY.Open(
          self.client_ids[0], mode="rw", token=self.token) as client_obj:
        client_obj.AddLabel(u"common_test_label", owner=self.token.username)
        client_obj.AddLabel(u"unique_test_label", owner=self.token.username)

        # Add user in knowledge base.
        kb = client_obj.Get(client_obj.Schema.KNOWLEDGE_BASE)
        kb.users.Append(rdf_client.User(username="sample_user"))
        kb.users.Append(rdf_client.User(username=self.token.username))
        client_obj.Set(client_obj.Schema.KNOWLEDGE_BASE, kb)

        # Update index, since we added users and labels.
        with client_index.CreateClientIndex(token=self.token) as index:
          index.AddClient(client_obj)

  def _WaitForSearchResults(self, target_count):
    self.WaitUntil(self.IsElementPresent, "css=grr-clients-list")

    if not target_count:
      # When we expect no elements at all, we have to check that Loading...
      # disappears and then nothing is displayed.
      self.WaitUntilNot(self.IsElementPresent, "css=tr:contains('Loading...')")
      self.WaitUntilEqual(target_count, self.GetCssCount,
                          "css=grr-clients-list tbody > tr")
    else:
      # When expect multiple elements we can just count all the rows that have
      # no "Loading..." init. Handling this case separately from target_count==0
      # case, since if we have enough elements in the result list, "Loading..."
      # label will go off-screen and therefore won't be removed from DOM
      # by Angular code (it has to actually be visible in order to be removed).
      self.WaitUntilEqual(
          target_count, self.GetCssCount,
          "css=grr-clients-list tbody > tr:not(:contains('Loading...'))")

  def testPageTitleChangesAccordingToQuery(self):
    self.Open("/#/search?q=foo")
    self.WaitUntilEqual("GRR | Search for \"foo\"", self.GetPageTitle)

    self.Type("client_query", text="host:Host-1", end_with_enter=True)
    self.WaitUntilEqual("GRR | Search for \"host:Host-1\"", self.GetPageTitle)

    # Not entering any search term checks for all clients.
    self.Open("/#/search")
    self.WaitUntilEqual("GRR | Client List", self.GetPageTitle)

  def testEmptySearchShowsAllClients(self):
    self.Open("/")
    self.Click("client_query_submit")

    # All 15 clients (10 default clients + 5 from setUp()) need to be found.
    self._WaitForSearchResults(target_count=15)

  def testSearchByClientId(self):
    client_name = self.client_ids[0].Basename()

    self.Open("/")
    self.Type("client_query", text=client_name, end_with_enter=True)

    self.WaitUntil(self.IsElementPresent,
                   "css=grr-clients-list tr:contains('%s') " % client_name)
    self._WaitForSearchResults(target_count=1)

  def testSearchWithHostKeyword(self):
    self.Open("/")

    # Host-1 exists, so we should find exactly one item.
    self.Type("client_query", text="host:Host-1", end_with_enter=True)

    self._WaitForSearchResults(target_count=1)

    # Host-99 does not exists, so we shouldn't find anything.
    self.Type("client_query", text="host:Host-99", end_with_enter=True)

    self._WaitForSearchResults(target_count=0)

    # The host keyword also searches FQDN, so we should find an item.
    self.Type(
        "client_query", text="host:Host-1.example.com", end_with_enter=True)

    self._WaitForSearchResults(target_count=1)

    # Unknown fqdns should yield an empty result.
    self.Type(
        "client_query", text="host:Host-99.example.com", end_with_enter=True)

    self._WaitForSearchResults(target_count=0)

  def testSearchWithLabelKeyword(self):
    self.Open("/")

    # Several client have this label, so we should find them all.
    self.Type(
        "client_query", text="label:common_test_label", end_with_enter=True)

    self._WaitForSearchResults(target_count=2)

    # Only one client has the unique label.
    self.Type(
        "client_query", text="label:unique_test_label", end_with_enter=True)

    self._WaitForSearchResults(target_count=1)

    # Only one client has the unique label.
    self.Type("client_query", text="label:unused_label", end_with_enter=True)

    self._WaitForSearchResults(target_count=0)

  def testSearchWithIPKeyword(self):
    self.Open("/")

    # IP contains the client number, so we should find exactly one item.
    self.Type("client_query", text="ip:192.168.0.1", end_with_enter=True)

    self._WaitForSearchResults(target_count=1)

    # Unknown ips should yield an empty result.
    self.Type("client_query", text="ip:192.168.32.0", end_with_enter=True)

    self._WaitForSearchResults(target_count=0)

  def testSearchWithMacKeyword(self):
    self.Open("/")

    # Mac contains the client number, so we should find exactly one item.
    self.Type("client_query", text="aabbccddee01", end_with_enter=True)

    self._WaitForSearchResults(target_count=1)

    # Unknown ips should yield an empty result.
    self.Type("client_query", text="aabbccddee99", end_with_enter=True)

    self._WaitForSearchResults(target_count=0)

  def testSearchWithUserKeyword(self):
    self.Open("/")

    self.Type(
        "client_query", text="user:" + self.token.username, end_with_enter=True)

    self._WaitForSearchResults(target_count=1)

    # Unknown users should yield an empty result.
    self.Type("client_query", text="user:I_do_not_exist", end_with_enter=True)

    self._WaitForSearchResults(target_count=0)

  def testSearchingForHuntIdOpensHunt(self):
    hunt_id = self.CreateHunt(description="demo hunt").urn.Basename()

    self.Open("/")
    self.Type("client_query", text=hunt_id, end_with_enter=True)
    self.WaitUntil(self.IsTextPresent, "GenericHunt")
    # This checks that Overview tab actually got updated.
    self.WaitUntil(self.IsTextPresent, "Total Network Traffic")

  def testSearchingForNonExistingHuntIdPerformsClientSearch(self):
    self.Open("/")

    # Hunt does not exist, so a client search should be performed.
    self.Type("client_query", text="H:12345678", end_with_enter=True)

    self._WaitForSearchResults(target_count=0)

  def testSearchingForLabelOpensTypeAheadDropdown(self):
    self.Open("/")

    # We need to retry the whole sequence of "clear->type->wait for dropdown",
    # as there's a potential race when we start typing before the
    # typeahead options are loaded. In this case the dropdown won't be shown,
    # and we need to type in the data one more time.
    def TypeAndGetDropdownCount():
      self.Type("client_query", text="")
      self.Type("client_query", text="common_")
      return self.GetCssCount("css=grr-search-box ul.dropdown-menu li")

    self.WaitUntilEqual(1, TypeAndGetDropdownCount)

    # If the popup is visible, check that clicking it will change the search
    # input.
    self.Click("css=grr-search-box ul.dropdown-menu li")
    self.WaitUntilEqual("label:common_test_label", self.GetValue,
                        "css=#client_query")

  def testBackButtonWorksAsExpected(self):
    self.RequestAndGrantClientApproval(self.client_ids[0])

    client_name = self.client_ids[0].Basename()

    self.Open("/#/clients/" + client_name)
    self.WaitUntil(self.IsTextPresent, client_name)
    # Check that correct navigation link is selected.
    self.WaitUntil(self.IsElementPresent,
                   "css=.active > a[grrtarget='client.hostInfo']")

    self.Click("css=a[grrtarget='client.launchFlows']")
    self.WaitUntil(self.IsTextPresent, "Please Select a flow to launch")
    # Check that correct navigation link is selected.
    self.WaitUntil(self.IsElementPresent,
                   "css=.active > a[grrtarget='client.launchFlows']")

    # Back button should bring us to host information again.
    self.Back()
    self.WaitUntil(self.IsTextPresent, client_name)
    # Check that correct navigation link is selected.
    self.WaitUntil(self.IsElementPresent,
                   "css=.active > a[grrtarget='client.hostInfo']")

    # Forward button should bring us to launch flows again.
    self.Forward()
    self.WaitUntil(self.IsTextPresent, "Please Select a flow to launch")
    # Check that correct navigation link is selected.
    self.WaitUntil(self.IsElementPresent,
                   "css=.active > a[grrtarget='client.launchFlows']")


class TestDefaultGUISettings(gui_test_lib.GRRSeleniumTest):

  def testDefaultGUISettingsWork(self):
    aff4.FACTORY.Delete(
        aff4.ROOT_URN.Add("users/%s" % self.token.username), token=self.token)

    self.Open("/")  # The ui displays an error here if the settings are invalid.

    self.WaitUntil(self.IsTextPresent, "Welcome to GRR")

    self.Click("css=grr-user-settings-button button")
    self.WaitUntil(self.IsTextPresent, "Settings")

    self.WaitUntil(self.IsTextPresent, "Mode")
    self.WaitUntilEqual("BASIC (default)", self.GetSelectedLabel,
                        "css=label:contains('Mode') ~ div.controls select")


if __name__ == "__main__":
  flags.StartMain(test_lib.main)
