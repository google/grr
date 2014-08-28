#!/usr/bin/env python
"""Tests for the collection export tool plugin."""


import argparse

# pylint: disable=unused-import, g-bad-import-order
from grr.lib import server_plugins
# pylint: enable=unused-import, g-bad-import-order

from grr.lib import aff4
from grr.lib import config_lib
from grr.lib import data_store
from grr.lib import email_alerts
from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib import utils
from grr.tools.export_plugins import collection_plugin


class CollectionExportPluginTest(test_lib.GRRBaseTest):

  def setUp(self):
    super(CollectionExportPluginTest, self).setUp()

    client_ids = self.SetupClients(1)
    self.client_id = client_ids[0]
    self.out = self.client_id.Add("fs/os")

    data_store.default_token = rdfvalue.ACLToken(username="user",
                                                 reason="reason")

  def testExportCollectionWithEmailPlugin(self):
    # Create a collection with URNs to some files.
    fd = aff4.FACTORY.Create("aff4:/testcoll", "RDFValueCollection",
                             token=self.token)
    fd.Add(rdfvalue.GrrMessage(payload=rdfvalue.StatEntry(
        aff4path=self.out.Add("testfile")),
                               source=self.client_id))
    fd.Close()

    plugin = collection_plugin.CollectionExportPlugin()
    parser = argparse.ArgumentParser()
    plugin.ConfigureArgParser(parser)

    def SendEmail(address, sender, title, message, **_):
      self.email_messages.append(dict(address=address, sender=sender,
                                      title=title, message=message))

    email_address = "notify@%s" % config_lib.CONFIG["Logging.domain"]
    with utils.Stubber(email_alerts, "SendEmail", SendEmail):
      self.email_messages = []

      plugin.Run(parser.parse_args(args=[
          "--path",
          "aff4:/testcoll",
          "email",
          "--email",
          email_address,
          "--email_limit",
          "100"]))

    self.assertEqual(len(self.email_messages), 1)
    for msg in self.email_messages:
      self.assertEqual(msg["address"], email_address)
      self.assertEqual("GRR Hunt results collection aff4:/testcoll got a new "
                       "result.", msg["title"])
      self.assertTrue("testfile" in msg["message"])


def main(argv):
  test_lib.main(argv)

if __name__ == "__main__":
  flags.StartMain(main)
