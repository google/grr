#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Test the hunt results interface."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


import mock

from grr_response_core.lib import flags
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_server import data_store
from grr_response_server.gui import api_call_router_with_approval_checks
from grr_response_server.gui import gui_test_lib
from grr_response_server.gui.api_plugins import hunt as api_hunt
from grr_response_server.output_plugins import csv_plugin
from grr_response_server.output_plugins import sqlite_plugin
from grr_response_server.output_plugins import yaml_plugin
from grr.test_lib import db_test_lib
from grr.test_lib import test_lib


@db_test_lib.DualDBTest
class TestHuntResultsView(gui_test_lib.GRRSeleniumHuntTest):

  def testHuntResultsView(self):
    self.CreateGenericHuntWithCollection()

    self.Open("/")
    self.WaitUntil(self.IsElementPresent, "client_query")
    self.Click("css=a[grrtarget=hunts]")

    self.WaitUntil(self.IsTextPresent, "GenericHunt")
    self.Click("css=td:contains('GenericHunt')")

    # Click the Results tab.
    self.Click("css=li[heading=Results]")

    self.WaitUntil(self.IsTextPresent, "aff4:/sample/1")
    self.WaitUntil(self.IsTextPresent,
                   "aff4:/%s/fs/os/c/bin/bash" % self.client_ids[0].Basename())
    self.WaitUntil(self.IsTextPresent, "aff4:/sample/3")

    self.RequestAndGrantClientApproval(self.client_ids[0].Basename())

    self.Click("link=aff4:/%s/fs/os/c/bin/bash" % self.client_ids[0].Basename())
    self.WaitUntil(self.IsElementPresent,
                   "css=li.active a:contains('Browse Virtual Filesystem')")

  def testClientSummaryModalIsShownWhenClientInfoButtonClicked(self):
    client_id = self.SetupClient(0)
    h = self.CreateSampleHunt()

    with data_store.DB.GetMutationPool() as pool:
      h.ResultCollection().Add(
          rdf_flows.GrrMessage(
              payload=rdfvalue.RDFString("foo-result"), source=client_id),
          mutation_pool=pool)

    self.Open("/#/hunts/%s/results" % h.urn.Basename())
    self.Click("css=td:contains('%s') button:has(.glyphicon-info-sign)" %
               client_id.Basename())

    self.WaitUntil(
        self.IsElementPresent,
        "css=.modal-dialog:contains('Client %s')" % client_id.Basename())

  def testResultsViewGetsAutoRefreshed(self):
    client_id = self.SetupClient(0)
    h = self.CreateSampleHunt()

    with data_store.DB.GetMutationPool() as pool:
      h.ResultCollection().Add(
          rdf_flows.GrrMessage(
              payload=rdfvalue.RDFString("foo-result"), source=client_id),
          mutation_pool=pool)

    self.Open("/")
    # Ensure auto-refresh updates happen every second.
    self.GetJavaScriptValue(
        "grrUi.core.resultsCollectionDirective.setAutoRefreshInterval(1000);")

    self.Click("css=a[grrtarget=hunts]")
    self.Click("css=td:contains('GenericHunt')")
    self.Click("css=li[heading=Results]")

    self.WaitUntil(self.IsElementPresent,
                   "css=grr-results-collection td:contains('foo-result')")
    self.WaitUntilNot(self.IsElementPresent,
                      "css=grr-results-collection td:contains('bar-result')")

    with data_store.DB.GetMutationPool() as pool:
      h.ResultCollection().Add(
          rdf_flows.GrrMessage(
              payload=rdfvalue.RDFString("bar-result"), source=client_id),
          mutation_pool=pool)

    self.WaitUntil(self.IsElementPresent,
                   "css=grr-results-collection td:contains('bar-result')")

  def testDownloadAsPanelNotShownForEmptyHuntResults(self):
    hunt_urn = self.CreateGenericHuntWithCollection([])

    self.Open("/#/hunts/%s/results" % hunt_urn.Basename())

    self.WaitUntil(self.IsTextPresent, "Value")
    self.WaitUntilNot(self.IsElementPresent, "css=grr-download-collection-as")

  @mock.patch.object(
      api_call_router_with_approval_checks.ApiCallRouterWithApprovalChecks,
      "GetExportedHuntResults",
      return_value=api_hunt.ApiGetExportedHuntResultsHandler())
  def testHuntResultsCanBeDownloadedAsCsv(self, mock_method):
    self.checkHuntResultsCanBeDownloadedAsType(
        mock_method, csv_plugin.CSVInstantOutputPlugin.plugin_name,
        csv_plugin.CSVInstantOutputPlugin.friendly_name)

  @mock.patch.object(
      api_call_router_with_approval_checks.ApiCallRouterWithApprovalChecks,
      "GetExportedHuntResults",
      return_value=api_hunt.ApiGetExportedHuntResultsHandler())
  def testHuntResultsCanBeDownloadedAsYaml(self, mock_method):
    self.checkHuntResultsCanBeDownloadedAsType(
        mock_method,
        yaml_plugin.YamlInstantOutputPluginWithExportConversion.plugin_name,
        yaml_plugin.YamlInstantOutputPluginWithExportConversion.friendly_name)

  @mock.patch.object(
      api_call_router_with_approval_checks.ApiCallRouterWithApprovalChecks,
      "GetExportedHuntResults",
      return_value=api_hunt.ApiGetExportedHuntResultsHandler())
  def testHuntResultsCanBeDownloadedAsSqlite(self, mock_method):
    self.checkHuntResultsCanBeDownloadedAsType(
        mock_method, sqlite_plugin.SqliteInstantOutputPlugin.plugin_name,
        sqlite_plugin.SqliteInstantOutputPlugin.friendly_name)

  def checkHuntResultsCanBeDownloadedAsType(self, mock_method, plugin,
                                            plugin_display_name):
    hunt_urn = self.CreateGenericHuntWithCollection()

    self.Open("/#/hunts/%s/results" % hunt_urn.Basename())
    self.Select("id=plugin-select", plugin_display_name)
    self.Click("css=grr-download-collection-as button[name='download-as']")

    def MockMethodIsCalled():
      try:
        # Mock should be called twice: once for HEAD (to check permissions)
        # and once for GET methods.
        mock_method.assert_called_with(
            api_hunt.ApiGetExportedHuntResultsArgs(
                hunt_id=hunt_urn.Basename(), plugin_name=plugin),
            token=mock.ANY)

        return True
      except AssertionError:
        return False

    self.WaitUntil(MockMethodIsCalled)


if __name__ == "__main__":
  flags.StartMain(test_lib.main)
