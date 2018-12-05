#!/usr/bin/env python
"""User dashboard tests."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


from builtins import range  # pylint: disable=redefined-builtin

from grr_response_core.lib import flags
from grr_response_core.lib import rdfvalue
from grr_response_server import access_control
from grr_response_server.gui import gui_test_lib
from grr.test_lib import db_test_lib
from grr.test_lib import test_lib


@db_test_lib.DualDBTest
class TestUserDashboard(gui_test_lib.SearchClientTestBase):
  """Tests for user dashboard shown on the home page."""

  def testShowsNothingByDefault(self):
    self.Open("/")
    self.WaitUntil(
        self.IsElementPresent, "css=grr-user-dashboard "
        "div[name=RecentlyAccessedClients]:contains('None')")
    self.WaitUntil(
        self.IsElementPresent, "css=grr-user-dashboard "
        "div[name=RecentlyCreatedHunts]:contains('None')")

  def testShowsHuntCreatedByCurrentUser(self):
    self.CreateSampleHunt("foo-description", token=self.token)

    self.Open("/")
    self.WaitUntil(
        self.IsElementPresent, "css=grr-user-dashboard "
        "div[name=RecentlyCreatedHunts]:contains('foo-description')")

  def testDoesNotShowHuntCreatedByAnotherUser(self):
    self.CreateSampleHunt(
        "foo", token=access_control.ACLToken(username="another"))

    self.Open("/")
    self.WaitUntil(
        self.IsElementPresent, "css=grr-user-dashboard "
        "div[name=RecentlyCreatedHunts]:contains('None')")

  def testClickingOnTheHuntRedirectsToThisHunt(self):
    self.CreateSampleHunt("foo-description", token=self.token)

    self.Open("/")
    self.Click("css=grr-user-dashboard "
               "div[name=RecentlyCreatedHunts] td:contains('foo-description')")
    self.WaitUntil(self.IsElementPresent, "css=grr-hunts-view")

  def testShows5LatestHunts(self):
    # Only hunts created in the last 31 days will get shown, so we have
    # to adjust their timestamps accordingly.
    timestamp = rdfvalue.RDFDatetime.Now() - rdfvalue.Duration("1d")
    for i in range(20):
      with test_lib.FakeTime(timestamp + rdfvalue.Duration(1000 * i)):
        if i % 2 == 0:
          descr = "foo-%d" % i
          token = access_control.ACLToken(username="another")
        else:
          descr = "bar-%d" % i
          token = self.token
        self.CreateSampleHunt(descr, token=token)

    self.Open("/")
    for i in range(11, 20, 2):
      self.WaitUntil(
          self.IsElementPresent, "css=grr-user-dashboard "
          "div[name=RecentlyCreatedHunts]:contains('bar-%d')" % i)

    self.WaitUntilNot(
        self.IsElementPresent, "css=grr-user-dashboard "
        "div[name=RecentlyCreatedHunts]:contains('foo')")

  def testDoesNotShowHuntsOlderThan31Days(self):
    now = rdfvalue.RDFDatetime.Now()
    with test_lib.FakeTime(now - rdfvalue.Duration("30d")):
      self.CreateSampleHunt("foo", token=self.token)

    with test_lib.FakeTime(now - rdfvalue.Duration("32d")):
      self.CreateSampleHunt("bar", token=self.token)

    with test_lib.FakeTime(now):
      self.Open("/")
      self.WaitUntil(
          self.IsElementPresent, "css=grr-user-dashboard "
          "div[name=RecentlyCreatedHunts]:contains('foo')")

      self.WaitUntilNot(
          self.IsElementPresent, "css=grr-user-dashboard "
          "div[name=RecentlyCreatedHunts]:contains('bar')")

  def testShowsClientWithRequestedApproval(self):
    client_id = self.SetupClient(0)
    self.RequestAndGrantClientApproval(client_id)

    self.Open("/")
    self.WaitUntil(
        self.IsElementPresent, "css=grr-user-dashboard "
        "div[name=RecentlyAccessedClients]"
        ":contains('%s')" % client_id.Basename())

  def testShowsClientTwiceIfTwoApprovalsWereRequested(self):
    client_id = self.SetupClient(0)
    self.RequestAndGrantClientApproval(
        client_id, requestor=self.token.username, reason="foo-reason")
    self.RequestAndGrantClientApproval(
        client_id, requestor=self.token.username, reason="bar-reason")

    self.Open("/")
    self.WaitUntil(
        self.IsElementPresent, "css=grr-user-dashboard "
        "div[name=RecentlyAccessedClients]:contains('foo-reason')")
    self.WaitUntil(
        self.IsElementPresent, "css=grr-user-dashboard "
        "div[name=RecentlyAccessedClients]:contains('bar-reason')")

  def testShowsMaxOf7Clients(self):
    client_ids = self.SetupClients(10)

    with test_lib.FakeTime(1000, 1):
      for c in client_ids:
        self.RequestAndGrantClientApproval(c)

    self.Open("/")
    for c in client_ids[3:]:
      self.WaitUntil(
          self.IsElementPresent, "css=grr-user-dashboard "
          "div[name=RecentlyAccessedClients]"
          ":contains('%s')" % c.Basename())

    for c in client_ids[:3]:
      self.WaitUntilNot(
          self.IsElementPresent, "css=grr-user-dashboard "
          "div[name=RecentlyAccessedClients]"
          ":contains('%s')" % c.Basename())

  def testValidApprovalIsNotMarked(self):
    client_id = self.SetupClient(0)
    self.RequestAndGrantClientApproval(client_id)

    self.Open("/")
    self.WaitUntil(
        self.IsElementPresent, "css=grr-user-dashboard "
        "div[name=RecentlyAccessedClients] "
        "tr:contains('%s')" % client_id.Basename())
    self.WaitUntilNot(
        self.IsElementPresent, "css=grr-user-dashboard "
        "div[name=RecentlyAccessedClients] "
        "tr:contains('%s').half-transparent" % client_id.Basename())

  def testNonValidApprovalIsMarked(self):
    client_id = self.SetupClient(0)
    self.RequestClientApproval(
        client_id.Basename(),
        reason=self.token.reason,
        approver=u"approver",
        requestor=self.token.username)

    self.Open("/")
    self.WaitUntil(
        self.IsElementPresent, "css=grr-user-dashboard "
        "div[name=RecentlyAccessedClients] "
        "tr:contains('%s').half-transparent" % client_id.Basename())

  def testClickingOnApprovalRedirectsToClient(self):
    client_id = self.SetupClient(0)
    self.RequestAndGrantClientApproval(client_id)

    self.Open("/")
    self.Click("css=grr-user-dashboard "
               "div[name=RecentlyAccessedClients] "
               "tr:contains('%s')" % client_id.Basename())

    self.WaitUntil(self.IsTextPresent, "Host-0")
    self.WaitUntil(self.IsTextPresent, client_id.Basename())


if __name__ == "__main__":
  flags.StartMain(test_lib.main)
