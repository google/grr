#!/usr/bin/env python
"""Tests for the main content view."""


import time

from grr.gui import runtests_test

# We have to import test_lib first to properly initialize aff4 and rdfvalues.
# pylint: disable=g-bad-import-order
from grr.lib import test_lib
# pylint: enable=g-bad-import-order

from grr.lib import aff4
from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib import utils
from grr.lib.aff4_objects import users as aff4_users
from grr.lib.rdfvalues import client as rdf_client


class SearchClientTestBase(test_lib.GRRSeleniumTest):
  pass


class TestNavigatorView(SearchClientTestBase):
  """Tests for NavigatorView (left side bar)."""

  def CreateClient(self, last_ping=None):
    if last_ping is None:
      last_ping = rdfvalue.RDFDatetime().Now()

    with self.ACLChecksDisabled():
      client_id = self.SetupClients(1)[0]
      with aff4.FACTORY.Open(
          client_id, mode="rw", token=self.token) as client_obj:
        client_obj.Set(client_obj.Schema.PING(last_ping))

      self.GrantClientApproval(client_id)

    client_obj = aff4.FACTORY.Open(client_id, token=self.token)
    return client_id

  def RecordCrash(self, client_id, timestamp):
    with utils.Stubber(time, "time", timestamp.AsSecondsFromEpoch):
      client = test_lib.CrashClientMock(client_id, self.token)
      for _ in test_lib.TestFlowHelper(
          "FlowWithOneClientRequest", client, client_id=client_id,
          token=self.token, check_flow_errors=False):
        pass

  def CreateClientWithVolumes(self, available=50):
    with self.ACLChecksDisabled():
      client_id = self.SetupClients(1)[0]
      with aff4.FACTORY.Open(
          client_id, mode="rw", token=self.token) as client_obj:
        volume = rdf_client.Volume(total_allocation_units=100,
                                   actual_available_allocation_units=available)
        client_obj.Set(client_obj.Schema.VOLUMES([volume]))

      self.GrantClientApproval(client_id)

    client_obj = aff4.FACTORY.Open(client_id, token=self.token)
    return client_id

  def testOnlineClientStatus(self):
    client_id = self.CreateClient()
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

  def testOnlineClientStatusInClientSearch(self):
    client_id = self.CreateClient()

    self.Open("/")
    self.Type("client_query", client_id.Basename())
    self.Click("client_query_submit")

    self.WaitUntil(self.IsElementPresent,
                   "css=tr:contains('%s') "
                   "img[src$='online.png']" % client_id.Basename())

  def testOneDayClientStatusInClientSearch(self):
    client_id = self.CreateClient(
        last_ping=rdfvalue.RDFDatetime().Now() - rdfvalue.Duration("1h"))

    self.Open("/")
    self.Type("client_query", client_id.Basename())
    self.Click("client_query_submit")

    self.WaitUntil(self.IsElementPresent,
                   "css=tr:contains('%s') "
                   "img[src$='online-1d.png']" % client_id.Basename())

  def testOfflineClientStatusInClientSearch(self):
    client_id = self.CreateClient(
        last_ping=rdfvalue.RDFDatetime().Now() - rdfvalue.Duration("1d"))

    self.Open("/")
    self.Type("client_query", client_id.Basename())
    self.Click("client_query_submit")

    self.WaitUntil(self.IsElementPresent,
                   "css=tr:contains('%s') "
                   "img[src$='offline.png']" % client_id.Basename())

  def testLatestCrashesStatusIsNotDisplayedWhenThereAreNoCrashes(self):
    client_id = self.CreateClient()
    self.Open("/#c=" + str(client_id))
    self.WaitUntil(self.IsTextPresent, "Host-0")
    self.WaitUntilNot(self.IsTextPresent, "Last crash")

  def testCrashIsDisplayedInClientStatus(self):
    timestamp = rdfvalue.RDFDatetime().Now()
    client_id = self.CreateClient(last_ping=timestamp)
    with self.ACLChecksDisabled():
      self.RecordCrash(client_id, timestamp - rdfvalue.Duration("5s"))
      self.GrantClientApproval(client_id)

    with utils.Stubber(time, "time",
                       lambda: float(timestamp.AsSecondsFromEpoch())):
      self.Open("/#c=" + str(client_id))
      self.WaitUntil(self.IsTextPresent, "Last crash")
      self.WaitUntil(self.IsTextPresent, "5 seconds ago")

  def testOnlyTheLatestCrashIsDisplayed(self):
    timestamp = rdfvalue.RDFDatetime().Now()
    client_id = self.CreateClient(last_ping=timestamp)
    with self.ACLChecksDisabled():
      self.RecordCrash(client_id, timestamp - rdfvalue.Duration("10s"))
      self.RecordCrash(client_id, timestamp - rdfvalue.Duration("5s"))
      self.GrantClientApproval(client_id)

    with utils.Stubber(time, "time",
                       lambda: float(timestamp.AsSecondsFromEpoch())):
      self.Open("/#c=" + str(client_id))
      self.WaitUntil(self.IsTextPresent, "Last crash")
      self.WaitUntil(self.IsTextPresent, "5 seconds ago")
      # This one is not displayed, because it exceeds the limit.
      self.WaitUntilNot(self.IsTextPresent, "10 seconds ago")

  def testOnlyCrashesHappenedInPastWeekAreDisplayed(self):
    timestamp = rdfvalue.RDFDatetime().Now()
    client_id = self.CreateClient(last_ping=timestamp)
    with self.ACLChecksDisabled():
      self.RecordCrash(client_id, timestamp - rdfvalue.Duration("8d"))
      self.GrantClientApproval(client_id)

    with utils.Stubber(time, "time",
                       lambda: float(timestamp.AsSecondsFromEpoch())):
      self.Open("/#c=" + str(client_id))
      self.WaitUntil(self.IsTextPresent, "Host-0")
      # This one is not displayed, because it happened more than 24 hours ago.
      self.WaitUntilNot(self.IsTextPresent, "Last crash")
      self.WaitUntilNot(self.IsTextPresent, "8 days ago")

  def testCrashIconDoesNotAppearInClientSearchWhenClientDidNotCrash(self):
    client_id = self.CreateClient()

    self.Open("/")
    self.Type("client_query", client_id.Basename())
    self.Click("client_query_submit")

    # There should be a result row with the client id.
    self.WaitUntil(self.IsElementPresent,
                   "css=tr:contains('%s')" % client_id.Basename())
    # But it shouldn't have the skull.
    self.WaitUntilNot(
        self.IsElementPresent,
        "css=tr:contains('%s') "
        "img[src$='skull-icon.png']" % client_id.Basename())

  def testCrashIconDoesNotAppearInClientSearchIfClientCrashedLongTimeAgo(self):
    client_id = self.CreateClient()
    with self.ACLChecksDisabled():
      self.RecordCrash(client_id,
                       rdfvalue.RDFDatetime().Now() - rdfvalue.Duration("25h"))

    self.Open("/")
    self.Type("client_query", client_id.Basename())
    self.Click("client_query_submit")

    # There should be a result row with the client id.
    self.WaitUntil(self.IsElementPresent,
                   "css=tr:contains('%s')" % client_id.Basename())
    # But it shouldn't have the skull.
    self.WaitUntilNot(
        self.IsElementPresent,
        "css=tr:contains('%s') "
        "img[src$='skull-icon.png']" % client_id.Basename())

  def testCrashIconAppearsInClientSearchIfClientCrashedRecently(self):
    timestamp = rdfvalue.RDFDatetime().Now()
    client_id = self.CreateClient()
    with self.ACLChecksDisabled():
      self.RecordCrash(client_id, timestamp)

    self.Open("/")
    self.Type("client_query", client_id.Basename())
    self.Click("client_query_submit")

    # There should be a result row with the client id.
    self.WaitUntil(self.IsElementPresent,
                   "css=tr:contains('%s')" % client_id.Basename())
    # And it should have the skull.
    self.WaitUntil(
        self.IsElementPresent,
        "css=tr:contains('%s') "
        "img[src$='skull-icon.png']" % client_id.Basename())

  def testDiskIconDoesNotAppearInClientSearchIfDiskIsNotFull(self):
    client_id = self.CreateClientWithVolumes()
    self.Open("/")
    self.Type("client_query", client_id.Basename())
    self.Click("client_query_submit")

    # There should be a result row with the client id.
    self.WaitUntil(self.IsElementPresent,
                   "css=tr:contains('%s')" % client_id.Basename())

    # But it shouldn't have the disk icon.
    self.WaitUntilNot(
        self.IsElementPresent,
        "css=tr:contains('%s') "
        "img[src$='hdd-bang-icon.png']" % client_id.Basename())

  def testDiskIconDoesAppearsInClientSearchIfDiskIsFull(self):
    client_id = self.CreateClientWithVolumes(available=1)
    self.Open("/")
    self.Type("client_query", client_id.Basename())
    self.Click("client_query_submit")

    # There should be a result row with the client id.
    self.WaitUntil(self.IsElementPresent,
                   "css=tr:contains('%s')" % client_id.Basename())

    # With the disk icon.
    self.WaitUntil(
        self.IsElementPresent,
        "css=tr:contains('%s') "
        "img[src$='hdd-bang-icon.png']" % client_id.Basename())

  def testDiskWarningIsNotDisplayed(self):
    client_id = self.CreateClientWithVolumes()
    self.Open("/#c=" + str(client_id))
    self.WaitUntil(self.IsTextPresent, "Host-0")
    self.WaitUntilNot(self.IsTextPresent, "Disk free space")

  def testDiskWarningIsDisplayed(self):
    client_id = self.CreateClientWithVolumes(available=1)
    self.Open("/#c=" + str(client_id))
    self.WaitUntil(self.IsTextPresent, "Host-0")
    self.WaitUntil(self.IsTextPresent, "Disk free space")


class TestContentView(SearchClientTestBase):
  """Tests the main content view."""

  def testGlobalNotificationIsShownWhenSet(self):
    with self.ACLChecksDisabled():
      with aff4.FACTORY.Create(aff4.GlobalNotificationStorage.DEFAULT_PATH,
                               aff4_type="GlobalNotificationStorage",
                               mode="rw", token=self.token) as storage:
        storage.AddNotification(
            aff4_users.GlobalNotification(
                type=aff4_users.GlobalNotification.Type.ERROR,
                header="Oh no, we're doomed!",
                content="Houston, Houston, we have a prob...",
                link="http://www.google.com"
            ))

    self.Open("/")
    self.WaitUntil(self.IsTextPresent, "Houston, Houston, we have a prob...")

  def testNotificationsOfDifferentTypesAreShownTogether(self):
    with self.ACLChecksDisabled():
      with aff4.FACTORY.Create(aff4.GlobalNotificationStorage.DEFAULT_PATH,
                               aff4_type="GlobalNotificationStorage",
                               mode="rw", token=self.token) as storage:
        storage.AddNotification(
            aff4_users.GlobalNotification(
                type=aff4_users.GlobalNotification.Type.ERROR,
                header="Oh no, we're doomed!",
                content="Houston, Houston, we have a prob...",
                link="http://www.google.com"
            ))
        storage.AddNotification(
            aff4_users.GlobalNotification(
                type=aff4_users.GlobalNotification.Type.INFO,
                header="Nothing to worry about!",
                link="http://www.google.com"
            ))

    self.Open("/")
    self.WaitUntil(self.IsTextPresent, "Houston, Houston, we have a prob...")
    self.WaitUntil(self.IsTextPresent, "Nothing to worry about!")

  def testNewNotificationReplacesPreviousNotificationOfTheSameType(self):
    with self.ACLChecksDisabled():
      with aff4.FACTORY.Create(aff4.GlobalNotificationStorage.DEFAULT_PATH,
                               aff4_type="GlobalNotificationStorage",
                               mode="rw", token=self.token) as storage:
        storage.AddNotification(
            aff4_users.GlobalNotification(
                type=aff4_users.GlobalNotification.Type.ERROR,
                header="Oh no, we're doomed!",
                content="Houston, Houston, we have a prob...",
                link="http://www.google.com"
            ))

    self.Open("/")
    self.WaitUntil(self.IsTextPresent, "Houston, Houston, we have a prob...")

    with self.ACLChecksDisabled():
      with aff4.FACTORY.Create(aff4.GlobalNotificationStorage.DEFAULT_PATH,
                               aff4_type="GlobalNotificationStorage",
                               mode="rw", token=self.token) as storage:
        storage.AddNotification(
            aff4_users.GlobalNotification(
                type=aff4_users.GlobalNotification.Type.ERROR,
                content="Too late to do anything!",
                link="http://www.google.com"
            ))

    self.Open("/")
    self.WaitUntil(self.IsTextPresent, "Too late to do anything!")
    self.assertFalse(self.IsTextPresent("Houston, Houston, we have a prob..."))

  def testGlobalNotificationDisappearsAfterClosing(self):
    with self.ACLChecksDisabled():
      with aff4.FACTORY.Create(aff4.GlobalNotificationStorage.DEFAULT_PATH,
                               aff4_type="GlobalNotificationStorage",
                               mode="rw", token=self.token) as storage:
        storage.AddNotification(
            aff4_users.GlobalNotification(
                type=aff4_users.GlobalNotification.Type.ERROR,
                header="Oh no, we're doomed!",
                content="Houston, Houston, we have a prob...",
                link="http://www.google.com"
            ))

    self.Open("/")
    self.WaitUntil(self.IsTextPresent, "Houston, Houston, we have a prob...")

    self.Click("css=#global-notification button.close")
    self.WaitUntilNot(self.IsTextPresent, "Houston, Houston, we have a prob...")

    self.Open("/")
    self.WaitUntil(self.IsElementPresent, "client_query")
    self.WaitUntilNot(self.IsTextPresent, "Houston, Houston, we have a prob...")

  def testClosingOneNotificationLeavesAnotherIntact(self):
    with self.ACLChecksDisabled():
      with aff4.FACTORY.Create(aff4.GlobalNotificationStorage.DEFAULT_PATH,
                               aff4_type="GlobalNotificationStorage",
                               mode="rw", token=self.token) as storage:
        storage.AddNotification(
            aff4_users.GlobalNotification(
                type=aff4_users.GlobalNotification.Type.ERROR,
                header="Oh no, we're doomed!",
                content="Houston, Houston, we have a prob...",
                link="http://www.google.com"
            ))
        storage.AddNotification(
            aff4_users.GlobalNotification(
                type=aff4_users.GlobalNotification.Type.INFO,
                header="Nothing to worry about!",
                link="http://www.google.com"
            ))

    self.Open("/")
    self.WaitUntil(self.IsTextPresent, "Houston, Houston, we have a prob...")

    self.Click("css=#global-notification .alert-error button.close")
    self.WaitUntilNot(self.IsTextPresent, "Houston, Houston, we have a prob...")
    self.WaitUntil(self.IsTextPresent, "Nothing to worry about!")

    self.Open("/")
    self.WaitUntil(self.IsTextPresent, "Nothing to worry about!")
    self.assertFalse(self.IsTextPresent("Houston, Houston, we have a prob..."))

  def testGlobalNotificationIsSetViaGlobalFlow(self):
    with self.ACLChecksDisabled():
      self.CreateAdminUser("test")

    self.Open("/")
    self.WaitUntil(self.IsElementPresent, "client_query")
    self.WaitUntilNot(self.IsTextPresent, "Houston, Houston, we have a prob...")

    self.Click("css=a[grrtarget=GlobalLaunchFlows]")
    self.Click("css=#_Administrative")
    self.Click("link=SetGlobalNotification")

    self.Type("css=input#args-header", "Oh no, we're doomed!")
    self.Type("css=input#args-content", "Houston, Houston, we have a prob...")

    self.Click("css=button.Launch")

    self.Open("/")
    self.WaitUntil(self.IsTextPresent, "Oh no, we're doomed!")
    self.WaitUntil(self.IsTextPresent, "Houston, Houston, we have a prob...")

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
    self.Click("css=grr-user-settings-button")
    self.Click("css=.form-group:has(label:contains('Canary mode')) input")
    self.Click("css=button[name=Proceed]")

    # Page should get updated and now canary mode should be on.
    self.WaitUntil(self.IsTextPresent, "CANARY MODE IS ON")

    # Go to the user settings and turn canary mode off.
    self.Click("css=grr-user-settings-button")
    self.Click("css=.form-group:has(label:contains('Canary mode')) input")
    self.Click("css=button[name=Proceed]")

    # Page should get updated and now canary mode should be off.
    self.WaitUntil(self.IsTextPresent, "CANARY MODE IS OFF")


class TestHostTable(SearchClientTestBase):
  """Tests the main content view."""

  def testUserLabelIsShownAsBootstrapSuccessLabel(self):
    with self.ACLChecksDisabled():
      with aff4.FACTORY.Open("C.0000000000000001", mode="rw",
                             token=self.token) as client:
        client.AddLabels("foo", owner="test")

    self.Open("/#main=HostTable")

    self.WaitUntil(self.IsVisible,
                   "css=tr:contains('C.0000000000000001') "
                   "span.label-success:contains('foo')")

  def testSystemLabelIsShownAsRegularBootstrapLabel(self):
    with self.ACLChecksDisabled():
      with aff4.FACTORY.Open("C.0000000000000001", mode="rw",
                             token=self.token) as client:
        client.AddLabels("bar", owner="GRR")

    self.Open("/#main=HostTable")
    self.WaitUntil(self.IsVisible,
                   "css=tr:contains('C.0000000000000001') "
                   "span.label:not(.label-success):contains('bar')")

  def testLabelButtonIsDisabledByDefault(self):
    self.Open("/#main=HostTable")
    self.WaitUntil(self.IsVisible,
                   "css=button[name=AddLabels][disabled]")

  def testLabelButtonIsEnabledWhenClientIsSelected(self):
    self.Open("/#main=HostTable")

    self.WaitUntil(self.IsVisible,
                   "css=button[name=AddLabels][disabled]")
    self.Click("css=input.client-checkbox["
               "client_urn='aff4:/C.0000000000000001']")
    self.WaitUntilNot(self.IsVisible,
                      "css=button[name=AddLabels][disabled]")

  def testAddClientsLabelsDialogShowsListOfSelectedClients(self):
    self.Open("/#main=HostTable")

    # Select 3 clients and click 'Add Label' button.
    self.Click("css=input.client-checkbox["
               "client_urn='aff4:/C.0000000000000001']")
    self.Click("css=input.client-checkbox["
               "client_urn='aff4:/C.0000000000000003']")
    self.Click("css=input.client-checkbox["
               "client_urn='aff4:/C.0000000000000007']")
    self.Click("css=button[name=AddLabels]:not([disabled])")

    # Check that all 3 client ids are shown in the dialog.
    self.WaitUntil(self.IsVisible,
                   "css=div[name=AddClientsLabelsDialog]:"
                   "contains('C.0000000000000001')")
    self.WaitUntil(self.IsVisible,
                   "css=div[name=AddClientsLabelsDialog]:"
                   "contains('C.0000000000000003')")
    self.WaitUntil(self.IsVisible,
                   "css=div[name=AddClientsLabelsDialog]:"
                   "contains('C.0000000000000007')")

  def testAddClientsLabelsDialogShowsErrorWhenAddingLabelWithComma(self):
    self.Open("/#main=HostTable")

    # Select 1 client and click 'Add Label' button.
    self.Click("css=input.client-checkbox["
               "client_urn='aff4:/C.0000000000000001']")
    self.Click("css=button[name=AddLabels]:not([disabled])")

    # Type label name
    self.Type("css=div[name=AddClientsLabelsDialog] input[name=labelBox]",
              "a,b")

    # Click proceed and check that error message is displayed and that
    # dialog is not going away.
    self.Click("css=div[name=AddClientsLabelsDialog] button[name=Proceed]")
    self.WaitUntil(self.IsTextPresent, "Label name can only contain")
    self.WaitUntil(self.IsVisible, "css=div[name=AddClientsLabelsDialog]")

  def testLabelIsAppliedCorrectlyViaAddClientsLabelsDialog(self):
    self.Open("/#main=HostTable")

    # Select 1 client and click 'Add Label' button.
    self.Click("css=input.client-checkbox["
               "client_urn='aff4:/C.0000000000000001']")
    self.Click("css=button[name=AddLabels]:not([disabled])")

    # Type label name.
    self.Type("css=div[name=AddClientsLabelsDialog] input[name=labelBox]",
              "issue 42")

    # Click proceed and check that success message is displayed and that
    # proceed button is replaced with close button.
    self.Click("css=div[name=AddClientsLabelsDialog] button[name=Proceed]")
    self.WaitUntil(self.IsTextPresent, "Label was successfully added")
    self.WaitUntilNot(self.IsVisible,
                      "css=div[name=AddClientsLabelsDialog] "
                      "button[name=Proceed]")

    # Click on "Close" button and check that dialog has disappeared.
    self.Click("css=div[name=AddClientsLabelsDialog] button[name=Close]")
    self.WaitUntilNot(self.IsVisible,
                      "css=div[name=AddClientsLabelsDialog]")

    # Check that label has appeared in the clients list.
    self.WaitUntil(self.IsVisible,
                   "css=tr:contains('C.0000000000000001') "
                   "span.label-success:contains('issue 42')")

  def testAppliedLabelBecomesSearchableImmediately(self):
    self.Open("/#main=HostTable")

    # Select 1 client and click 'Add Label' button.
    self.Click("css=input.client-checkbox["
               "client_urn='aff4:/C.0000000000000001']")
    self.Click("css=button[name=AddLabels]:not([disabled])")

    # Type label name.
    self.Type("css=div[name=AddClientsLabelsDialog] input[name=labelBox]",
              "issue 42")

    # Click proceed and check that success message is displayed and that
    # proceed button is replaced with close button.
    self.Click("css=div[name=AddClientsLabelsDialog] button[name=Proceed]")
    self.WaitUntil(self.IsTextPresent, "Label was successfully added")
    self.WaitUntilNot(self.IsVisible,
                      "css=div[name=AddClientsLabelsDialog] "
                      "button[name=Proceed]")

    # Click on "Close" button and check that dialog has disappeared.
    self.Click("css=div[name=AddClientsLabelsDialog] button[name=Close]")
    self.WaitUntilNot(self.IsVisible,
                      "css=div[name=AddClientsLabelsDialog]")

    # Open client search with label and check that labeled client is shown.
    self.Open("/#main=HostTable&q=label:\"issue 42\"")
    self.WaitUntil(self.IsTextPresent, "C.0000000000000001")

  def testSelectionIsPreservedWhenAddClientsLabelsDialogIsCancelled(self):
    self.Open("/#main=HostTable")

    # Select 1 client and click 'Add Label' button.
    self.Click("css=input.client-checkbox["
               "client_urn='aff4:/C.0000000000000001']")
    self.Click("css=button[name=AddLabels]:not([disabled])")

    # Click on "Cancel" button and check that dialog has disappeared.
    self.Click("css=div[name=AddClientsLabelsDialog] button[name=Cancel]")
    self.WaitUntilNot(self.IsVisible,
                      "css=div[name=AddClientsLabelsDialog]")

    # Ensure that checkbox is still checked
    self.WaitUntil(self.IsVisible,
                   "css=input.client-checkbox["
                   "client_urn='aff4:/C.0000000000000001']:checked")

  def testSelectionIsResetWhenLabelIsAppliedViaAddClientsLabelsDialog(self):
    self.Open("/#main=HostTable")

    # Select 1 client and click 'Add Label' button.
    self.Click("css=input.client-checkbox["
               "client_urn='aff4:/C.0000000000000001']")
    self.Click("css=button[name=AddLabels]:not([disabled])")

    # Type label name, click on "Proceed" and "Close" buttons.
    self.Type("css=div[name=AddClientsLabelsDialog] input[name=labelBox]",
              "issue 42")
    self.Click("css=div[name=AddClientsLabelsDialog] button[name=Proceed]")
    self.Click("css=div[name=AddClientsLabelsDialog] button[name=Close]")

    # Ensure that checkbox is not checked anymore.
    self.WaitUntil(self.IsVisible,
                   "css=input.client-checkbox["
                   "client_urn='aff4:/C.0000000000000001']:not(:checked)")

  def testCheckAllCheckboxSelectsAllClients(self):
    self.Open("/#main=HostTable")

    self.WaitUntil(self.IsTextPresent, "C.0000000000000001")

    # Check that checkboxes for certain clients are unchecked.
    self.WaitUntil(self.IsVisible,
                   "css=input.client-checkbox["
                   "client_urn='aff4:/C.0000000000000001']:not(:checked)")
    self.WaitUntil(self.IsVisible,
                   "css=input.client-checkbox["
                   "client_urn='aff4:/C.0000000000000004']:not(:checked)")
    self.WaitUntil(self.IsVisible,
                   "css=input.client-checkbox["
                   "client_urn='aff4:/C.0000000000000007']:not(:checked)")

    # Click on 'check all checkbox'
    self.Click("css=input.client-checkbox.select-all")

    # Check that checkboxes for certain clients are now checked.
    self.WaitUntil(self.IsVisible,
                   "css=input.client-checkbox["
                   "client_urn='aff4:/C.0000000000000001']:checked")
    self.WaitUntil(self.IsVisible,
                   "css=input.client-checkbox["
                   "client_urn='aff4:/C.0000000000000004']:checked")
    self.WaitUntil(self.IsVisible,
                   "css=input.client-checkbox["
                   "client_urn='aff4:/C.0000000000000007']:checked")

    # Click once more on 'check all checkbox'.
    self.Click("css=input.client-checkbox.select-all")

    # Check that checkboxes for certain clients are now again unchecked.
    self.WaitUntil(self.IsVisible,
                   "css=input.client-checkbox["
                   "client_urn='aff4:/C.0000000000000001']:not(:checked)")
    self.WaitUntil(self.IsVisible,
                   "css=input.client-checkbox["
                   "client_urn='aff4:/C.0000000000000004']:not(:checked)")
    self.WaitUntil(self.IsVisible,
                   "css=input.client-checkbox["
                   "client_urn='aff4:/C.0000000000000007']:not(:checked)")

  def testClientsSelectedWithSelectAllAreShownInAddClientsLabelsDialog(self):
    self.Open("/#main=HostTable")

    self.WaitUntil(self.IsTextPresent, "C.0000000000000001")

    # Click on 'check all checkbox'.
    self.Click("css=input.client-checkbox.select-all")

    # Click on 'Apply Label' button.
    self.Click("css=button[name=AddLabels]:not([disabled])")

    # Check that client ids are shown in the dialog.
    self.WaitUntil(self.IsVisible,
                   "css=div[name=AddClientsLabelsDialog]:"
                   "contains('C.0000000000000001')")
    self.WaitUntil(self.IsVisible,
                   "css=div[name=AddClientsLabelsDialog]:"
                   "contains('C.0000000000000004')")
    self.WaitUntil(self.IsVisible,
                   "css=div[name=AddClientsLabelsDialog]:"
                   "contains('C.0000000000000007')")


def main(argv):
  # Run the full test suite
  runtests_test.SeleniumTestProgram(argv=argv)

if __name__ == "__main__":
  flags.StartMain(main)
