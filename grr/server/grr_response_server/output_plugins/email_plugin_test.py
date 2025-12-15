#!/usr/bin/env python
"""Tests for email output plugin."""

from unittest import mock

from absl import app
from absl.testing import absltest

from grr_response_core.lib import rdfvalue
from grr_response_proto import flows_pb2
from grr_response_proto import objects_pb2
from grr_response_proto import output_plugin_pb2
from grr_response_proto import sysinfo_pb2
from grr_response_server import email_alerts
from grr_response_server.databases import db as abstract_db
from grr_response_server.databases import db_test_utils
from grr_response_server.output_plugins import email_plugin
from grr.test_lib import db_test_lib
from grr.test_lib import test_lib


class EmailOutputPluginTest(absltest.TestCase):
  """Tests email output plugin."""

  @db_test_lib.WithDatabase
  def testEmailPluginSendsEmailPerEveyBatchOfResponses(
      self, db: abstract_db.Database
  ):
    # Setup is needed for `ReadClientSnapshot`
    client_id = db_test_utils.InitializeClient(db)
    db.WriteClientMetadata(client_id)

    snapshot = objects_pb2.ClientSnapshot()
    snapshot.client_id = client_id
    snapshot.knowledge_base.fqdn = "somehostname"
    snapshot.knowledge_base.os = "Linux"
    db.WriteClientSnapshot(snapshot)

    flow_result = flows_pb2.FlowResult(
        client_id=client_id,
    )
    flow_result.payload.Pack(sysinfo_pb2.Process(pid=42))

    flow_urn = rdfvalue.RDFURN("{}/flows/{}".format(client_id, "ABCDE"))
    plugin = email_plugin.EmailOutputPlugin(
        source_urn=flow_urn,
        args=output_plugin_pb2.EmailOutputPluginArgs(
            email_address="notify@example.com"
        ),
    )

    email_messages = []
    def SendEmail(address, sender, title, message, **_):
      email_messages.append(
          dict(address=address, sender=sender, title=title, message=message)
      )

    with mock.patch.object(email_alerts.EMAIL_ALERTER, "SendEmail", SendEmail):
      plugin.ProcessResults(responses=[flow_result, flow_result])
      # In this case does nothing, but should always be called after
      # ProcessResults.
      plugin.Flush()

    self.assertLen(email_messages, 1)

    msg = email_messages[0]
    self.assertEqual(msg["address"], "notify@example.com")
    self.assertIn(
        f"got a new result batch in aff4:/{client_id}/flows/ABCDE", msg["title"]
    )
    self.assertIn("(size 2)", msg["message"])
    self.assertIn(client_id, msg["message"])
    self.assertIn("somehostname", msg["message"])


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
