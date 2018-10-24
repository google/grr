#!/usr/bin/env python
"""Tests for fleetspeak_utils module."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import mock

from grr_response_core.lib import flags
from grr_response_server import fleetspeak_utils
from grr.test_lib import fleetspeak_test_lib
from grr.test_lib import test_lib

from fleetspeak.src.common.proto.fleetspeak import common_pb2
from fleetspeak.src.server.proto.fleetspeak_server import admin_pb2


def MockConnReturningClient(client):
  conn = mock.MagicMock()
  conn.outgoing.ListClients.return_value = admin_pb2.ListClientsResponse(
      clients=[client])
  return conn


class FleetspeakUtilsTest(test_lib.GRRBaseTest):

  def testGetLabelFromFleetspeakUnknown(self):
    client_id = "C.0000000000000001"
    conn = MockConnReturningClient(
        admin_pb2.Client(
            client_id=fleetspeak_utils.GRRIDToFleetspeakID(client_id),
            labels=[common_pb2.Label(service_name="client",
                                     label="division2")]))
    with test_lib.ConfigOverrider({
        "Server.fleetspeak_label_map": ["division1:fleetspeak-division1"],
    }):
      with fleetspeak_test_lib.ConnectionOverrider(conn):
        self.assertEqual("fleetspeak-unknown",
                         fleetspeak_utils.GetLabelFromFleetspeak(client_id))

  def testGetLabelFromFleetspeakKnown(self):
    client_id = "C.0000000000000001"
    conn = MockConnReturningClient(
        admin_pb2.Client(
            client_id=fleetspeak_utils.GRRIDToFleetspeakID(client_id),
            labels=[common_pb2.Label(service_name="client",
                                     label="division1")]))
    with test_lib.ConfigOverrider({
        "Server.fleetspeak_label_map": ["division1:fleetspeak-division1"],
    }):
      with fleetspeak_test_lib.ConnectionOverrider(conn):
        self.assertEqual("fleetspeak-division1",
                         fleetspeak_utils.GetLabelFromFleetspeak(client_id))


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
