#!/usr/bin/env python
"""FS GRR server side integration utility functions."""

import binascii

from fleetspeak.src.common.proto.fleetspeak import common_pb2 as fs_common_pb2

from grr.lib.rdfvalues import client as rdf_client
from grr.server import aff4
from grr.server import fleetspeak_connector


def IsFleetspeakEnabledClient(grr_id, token):
  if grr_id is None:
    return False

  with aff4.FACTORY.Create(
      rdf_client.ClientURN(grr_id),
      aff4.AFF4Object.classes["VFSGRRClient"],
      mode="r",
      token=token) as client:
    fs_enabled = bool(client.Get(client.Schema.FLEETSPEAK_ENABLED))
    return fs_enabled


def SendGrrMessageThroughFleetspeak(grr_id, msg):
  """Sends the given GrrMessage through FS."""
  fs_msg = fs_common_pb2.Message(
      message_type="GrrMessage",
      destination=fs_common_pb2.Address(
          client_id=GRRIDToFleetspeakID(grr_id), service_name="GRR"))
  fs_msg.data.Pack(msg.AsPrimitiveProto())
  fleetspeak_connector.CONN.Send(fs_msg)


def FleetspeakIDToGRRID(fs_id):
  return "C." + binascii.hexlify(fs_id)


def GRRIDToFleetspeakID(grr_id):
  # Strip the 'C.' prefix and convert to binary.
  return binascii.unhexlify(grr_id[2:])
