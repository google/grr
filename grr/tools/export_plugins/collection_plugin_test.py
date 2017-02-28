#!/usr/bin/env python
"""Tests for the collection export tool plugin."""


import argparse

import mock

from grr.lib import access_control
from grr.lib import config_lib
from grr.lib import data_store
from grr.lib import email_alerts
from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib import utils
from grr.lib.hunts import results
from grr.lib.output_plugins import email_plugin
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import flows as rdf_flows
from grr.lib.rdfvalues import paths as rdf_paths
from grr.tools.export_plugins import collection_plugin


class CollectionExportPluginTest(test_lib.GRRBaseTest):

  def setUp(self):
    super(CollectionExportPluginTest, self).setUp()

    client_ids = self.SetupClients(1)
    self.client_id = client_ids[0]

    data_store.default_token = access_control.ACLToken(
        username="user", reason="reason")

  def testGetValuesForExportHuntResultCollection(self):
    fd = results.HuntResultCollection("aff4:/huntcoll", token=self.token)
    fd.Add(
        rdf_flows.GrrMessage(
            payload=rdf_client.StatEntry(pathspec=rdf_paths.PathSpec(
                path="testfile", pathtype="OS")),
            source=self.client_id))

    plugin = collection_plugin.CollectionExportPlugin()
    mock_args = mock.Mock()
    mock_args.path = rdfvalue.RDFURN("aff4:/huntcoll")
    mock_args.no_legacy_warning_pause = True
    self.assertEqual(len(plugin.GetValuesForExport(mock_args)), 1)

  def testExportCollectionWithEmailPlugin(self):
    # Create a collection with URNs to some files.
    fd = results.HuntResultCollection("aff4:/testcoll", token=self.token)
    fd.Add(
        rdf_flows.GrrMessage(
            payload=rdf_client.StatEntry(pathspec=rdf_paths.PathSpec(
                path="testfile", pathtype="OS")),
            source=self.client_id))

    plugin = collection_plugin.CollectionExportPlugin()
    parser = argparse.ArgumentParser()
    plugin.ConfigureArgParser(parser)

    def SendEmail(address, sender, title, message, **_):
      self.email_messages.append(
          dict(address=address, sender=sender, title=title, message=message))

    email_address = "notify@%s" % config_lib.CONFIG["Logging.domain"]
    with utils.Stubber(email_alerts.EMAIL_ALERTER, "SendEmail", SendEmail):
      self.email_messages = []

      plugin.Run(
          parser.parse_args(args=[
              "--no_legacy_warning_pause",
              "--path",
              "aff4:/testcoll",
              email_plugin.EmailOutputPlugin.name,
              "--email_address",
              email_address,
              "--emails_limit",
              "100",
          ]))

    self.assertEqual(len(self.email_messages), 1)
    for msg in self.email_messages:
      self.assertEqual(msg["address"], email_address)
      self.assertEqual("GRR got a new result in aff4:/testcoll.", msg["title"])
      self.assertTrue(
          "GRR got a new result in aff4:/testcoll" in msg["message"])
      self.assertTrue("(Host-0)" in msg["message"])


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
