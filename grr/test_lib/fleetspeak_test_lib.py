#!/usr/bin/env python
"""Fleetspeak-related helpers for use in tests."""

import collections
import threading
from typing import Optional, Text

from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_proto import jobs_pb2
from grr_response_server import fleetspeak_utils
from fleetspeak.src.common.proto.fleetspeak import common_pb2

_message_lock = threading.Lock()
_messages_by_client_id = {}


def StoreMessage(fs_msg: common_pb2.Message):
  """Emulates sending of a message to Fleetspeak by storing it in-memory."""
  if not fs_msg.destination.client_id:
    raise ValueError("No destination set for Fleetspeak message:\n%s" % fs_msg)

  grr_id = fleetspeak_utils.FleetspeakIDToGRRID(fs_msg.destination.client_id)
  raw_grr_msg = jobs_pb2.GrrMessage()
  fs_msg.data.Unpack(raw_grr_msg)
  grr_msg = rdf_flows.GrrMessage.FromSerializedBytes(
      raw_grr_msg.SerializeToString())
  with _message_lock:
    try:
      _messages_by_client_id[grr_id].append(grr_msg)
    except KeyError:
      _messages_by_client_id[grr_id] = collections.deque([grr_msg])


def PopMessage(client_id: Text) -> Optional[rdf_flows.GrrMessage]:
  """Returns a message sent to the given Fleetspeak client.

  The returned message is removed from the in-memory store. Messages for
  any given client are returned in the order in which they are inserted. If
  a client has no pending messages, None is returned.

  Args:
    client_id: GRR id of the Fleetspeak client to return a message for.
  """
  try:
    with _message_lock:
      return _messages_by_client_id[client_id].popleft()
  except (KeyError, IndexError):
    return None
