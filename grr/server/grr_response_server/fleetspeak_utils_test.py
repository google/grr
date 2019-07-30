#!/usr/bin/env python
"""Tests for fleetspeak_utils module."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from absl import app
import mock

from grr_response_server import fleetspeak_utils
from grr.test_lib import fleetspeak_test_lib
from grr.test_lib import test_lib

from fleetspeak.src.common.proto.fleetspeak import common_pb2
from fleetspeak.src.server.proto.fleetspeak_server import admin_pb2

_TEST_CLIENT_ID = "C.0000000000000001"


def _MockConnReturningClient(grr_id, labels):
  client = admin_pb2.Client(
      client_id=fleetspeak_utils.GRRIDToFleetspeakID(grr_id),
      labels=[common_pb2.Label(service_name=k, label=v) for k, v in labels])
  conn = mock.MagicMock()
  conn.outgoing.ListClients.return_value = admin_pb2.ListClientsResponse(
      clients=[client])
  return conn


class FleetspeakUtilsTest(test_lib.GRRBaseTest):

  def testGetLabelsFromFleetspeak_NoPrefix(self):
    conn = _MockConnReturningClient(_TEST_CLIENT_ID, [
        ("client", "foo-1"),
        ("client", "bar-2"),
        ("service-1", "foo-3"),
        ("service-1", "foo-4"),
        ("client", "foo-5"),
    ])

    with test_lib.ConfigOverrider({
        "Server.fleetspeak_label_map": ["foo-5:baz-5"],
    }):
      with fleetspeak_test_lib.ConnectionOverrider(conn):
        self.assertListEqual(
            fleetspeak_utils.GetLabelsFromFleetspeak(_TEST_CLIENT_ID),
            ["foo-1", "bar-2", "baz-5"])

  def testGetLabelsFromFleetspeak_Prefix(self):
    conn = _MockConnReturningClient(_TEST_CLIENT_ID, [
        ("client", "foo-1"),
        ("client", "bar-2"),
        ("service-1", "foo-3"),
        ("service-1", "foo-4"),
        ("client", "foo-5"),
    ])

    with test_lib.ConfigOverrider({
        "Server.fleetspeak_label_prefix": "foo",
        "Server.fleetspeak_label_map": ["foo-5: baz-5"],
    }):
      with fleetspeak_test_lib.ConnectionOverrider(conn):
        self.assertListEqual(
            fleetspeak_utils.GetLabelsFromFleetspeak(_TEST_CLIENT_ID),
            ["foo-1", "baz-5"])

  def testGetLabelsFromFleetspeak_NoLabels(self):
    conn = _MockConnReturningClient(_TEST_CLIENT_ID, [("service-1", "foo-3")])
    with fleetspeak_test_lib.ConnectionOverrider(conn):
      self.assertEmpty(
          fleetspeak_utils.GetLabelsFromFleetspeak(_TEST_CLIENT_ID))

  def testGetLabelsFromFleetspeak_UnknownClient(self):
    conn = mock.MagicMock()
    conn.outgoing.ListClients.return_value = admin_pb2.ListClientsResponse()
    with fleetspeak_test_lib.ConnectionOverrider(conn):
      self.assertEmpty(
          fleetspeak_utils.GetLabelsFromFleetspeak(_TEST_CLIENT_ID))


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
