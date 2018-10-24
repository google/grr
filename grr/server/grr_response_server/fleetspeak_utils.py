#!/usr/bin/env python
"""FS GRR server side integration utility functions."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import binascii

from fleetspeak.src.common.proto.fleetspeak import common_pb2 as fs_common_pb2
from fleetspeak.src.server.proto.fleetspeak_server import admin_pb2

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_server import aff4
from grr_response_server import data_store
from grr_response_server import fleetspeak_connector


def IsFleetspeakEnabledClient(grr_id, token=None):
  """Returns whether the provided GRR id is a Fleetspeak client."""
  if grr_id is None:
    return False

  if data_store.RelationalDBReadEnabled():
    md = data_store.REL_DB.ReadClientMetadata(grr_id)
    if not md:
      return False
    return md.fleetspeak_enabled

  else:
    with aff4.FACTORY.Create(
        rdf_client.ClientURN(grr_id),
        aff4.AFF4Object.classes["VFSGRRClient"],
        mode="r",
        token=token) as client:
      return bool(client.Get(client.Schema.FLEETSPEAK_ENABLED))


def SendGrrMessageThroughFleetspeak(grr_id, msg):
  """Sends the given GrrMessage through FS."""
  fs_msg = fs_common_pb2.Message(
      message_type="GrrMessage",
      destination=fs_common_pb2.Address(
          client_id=GRRIDToFleetspeakID(grr_id), service_name="GRR"))
  fs_msg.data.Pack(msg.AsPrimitiveProto())
  fleetspeak_connector.CONN.outgoing.InsertMessage(fs_msg)


def FleetspeakIDToGRRID(fs_id):
  return "C." + binascii.hexlify(fs_id)


def GRRIDToFleetspeakID(grr_id):
  # Strip the 'C.' prefix and convert to binary.
  return binascii.unhexlify(grr_id[2:])


def TSToRDFDatetime(ts):
  """Convert a protobuf.Timestamp to an RDFDatetime."""
  return rdfvalue.RDFDatetime(ts.seconds * 1000000 + ts.nanos // 1000)


def GetLabelFromFleetspeak(client_id):
  """Returns the primary GRR label to use for a fleetspeak client."""
  res = fleetspeak_connector.CONN.outgoing.ListClients(
      admin_pb2.ListClientsRequest(client_ids=[GRRIDToFleetspeakID(client_id)]))
  if not res.clients or not res.clients[0].labels:
    return fleetspeak_connector.unknown_label

  for label in res.clients[0].labels:
    if label.service_name != "client":
      continue
    if label.label in fleetspeak_connector.label_map:
      return fleetspeak_connector.label_map[label.label]

  return fleetspeak_connector.unknown_label
