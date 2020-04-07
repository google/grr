#!/usr/bin/env python
# Lint as: python3
"""User dashboard tests."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from absl import app

from grr_response_core.lib import rdfvalue
from grr_response_server.gui import gui_test_lib
from grr.test_lib import test_lib


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
    self.CreateSampleHunt("foo-description", creator=self.token.username)

    self.Open("/")
    self.WaitUntil(
        self.IsElementPresent, "css=grr-user-dashboard "
        "div[name=RecentlyCreatedHunts]:contains('foo-description')")

  def testDoesNotShowHuntCreatedByAnotherUser(self):
    self.CreateSampleHunt("foo", creator="another")

    self.Open("/")
    self.WaitUntil(
        self.IsElementPresent, "css=grr-user-dashboard "
        "div[name=RecentlyCreatedHunts]:contains('None')")

  def testClickingOnTheHuntRedirectsToThisHunt(self):
    self.CreateSampleHunt("foo-description", creator=self.token.username)

    self.Open("/")
    self.Click("css=grr-user-dashboard "
               "div[name=RecentlyCreatedHunts] td:contains('foo-description')")
    self.WaitUntil(self.IsElementPresent, "css=grr-hunts-view")

  def testShows5LatestHunts(self):
    # Only hunts created in the last 31 days will get shown, so we have
    # to adjust their timestamps accordingly.
    timestamp = rdfvalue.RDFDatetime.Now() - rdfvalue.Duration.From(
        1, rdfvalue.DAYS)
    for i in range(20):
      with test_lib.FakeTime(timestamp +
                             rdfvalue.Duration.From(1000 *
                                                    i, rdfvalue.SECONDS)):
        if i % 2 == 0:
          descr = "foo-%d" % i
          creator = "another"
        else:
          descr = "bar-%d" % i
          creator = self.token.username
        self.CreateSampleHunt(descr, creator=creator)

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
    with test_lib.FakeTime(now - rdfvalue.Duration.From(30, rdfvalue.DAYS)):
      self.CreateSampleHunt("foo", creator=self.token.username)

    with test_lib.FakeTime(now - rdfvalue.Duration.From(32, rdfvalue.DAYS)):
      self.CreateSampleHunt("bar", creator=self.token.username)

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
        ":contains('%s')" % client_id)

  def testShowsClientOnceIfTwoApprovalsWereRequested(self):
    client_id = self.SetupClient(0)
    self.RequestAndGrantClientApproval(
        client_id, requestor=self.token.username, reason="foo-reason")
    self.RequestAndGrantClientApproval(
        client_id, requestor=self.token.username, reason="bar-reason")

    self.Open("/")
    # Later approval request should take precedence.
    self.WaitUntil(
        self.IsElementPresent, "css=grr-user-dashboard "
        "div[name=RecentlyAccessedClients]:contains('bar-reason')")
    self.WaitUntilNot(
        self.IsElementPresent, "css=grr-user-dashboard "
        "div[name=RecentlyAccessedClients]:contains('foo-reason')")

  def testShowsMaxOf7Clients(self):
    client_ids = self.SetupClients(10)

    with test_lib.FakeTime(1000, 1):
      for client_id in client_ids:
        self.RequestAndGrantClientApproval(client_id)

    self.Open("/")
    for client_id in client_ids[3:]:
      self.WaitUntil(
          self.IsElementPresent, "css=grr-user-dashboard "
          "div[name=RecentlyAccessedClients]"
          ":contains('%s')" % client_id)

    for client_id in client_ids[:3]:
      self.WaitUntilNot(
          self.IsElementPresent, "css=grr-user-dashboard "
          "div[name=RecentlyAccessedClients]"
          ":contains('%s')" % client_id)

  def testValidApprovalIsNotMarked(self):
    client_id = self.SetupClient(0)
    self.RequestAndGrantClientApproval(client_id)

    self.Open("/")
    self.WaitUntil(
        self.IsElementPresent, "css=grr-user-dashboard "
        "div[name=RecentlyAccessedClients] "
        "tr:contains('%s')" % client_id)
    self.WaitUntilNot(
        self.IsElementPresent, "css=grr-user-dashboard "
        "div[name=RecentlyAccessedClients] "
        "tr:contains('%s').half-transparent" % client_id)

  def testNonValidApprovalIsMarked(self):
    client_id = self.SetupClient(0)
    self.RequestClientApproval(
        client_id,
        reason=self.token.reason,
        approver=u"approver",
        requestor=self.token.username)

    self.Open("/")
    self.WaitUntil(
        self.IsElementPresent, "css=grr-user-dashboard "
        "div[name=RecentlyAccessedClients] "
        "tr:contains('%s').half-transparent" % client_id)

  def testClickingOnApprovalRedirectsToClient(self):
    client_id = self.SetupClient(0)
    self.RequestAndGrantClientApproval(client_id)

    self.Open("/")
    self.Click("css=grr-user-dashboard "
               "div[name=RecentlyAccessedClients] "
               "tr:contains('%s')" % client_id)

    self.WaitUntil(self.IsTextPresent, "Host-0")
    self.WaitUntil(self.IsTextPresent, client_id)


if __name__ == "__main__":
  app.run(test_lib.main)
