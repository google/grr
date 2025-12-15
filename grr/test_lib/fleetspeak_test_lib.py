#!/usr/bin/env python
"""Fleetspeak-related helpers for use in tests."""

import collections
import functools
import threading
from typing import Optional
from unittest import mock

from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_proto import jobs_pb2
from grr_response_server import fleetspeak_connector
from grr_response_server import fleetspeak_utils
from fleetspeak.src.common.proto.fleetspeak import common_pb2
from fleetspeak.src.server.proto.fleetspeak_server import admin_pb2

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


def PopMessage(client_id: str) -> Optional[rdf_flows.GrrMessage]:
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


def WithFleetspeakConnector(func):
  """A decorator for Fleetspeak connector-dependent test methods.

  This decorator is intended for tests that might involve sending
  Fleetspeak messages or interacting with Fleetspeak connector.

  Args:
    func: A test method to be decorated.

  Returns:
    A Fleetspeak connector-aware function.
  """

  @functools.wraps(func)
  def Wrapper(*args, **kwargs):
    with mock.patch.object(fleetspeak_connector, "CONN") as mock_conn:
      mock_conn.outgoing.InsertMessage.side_effect = (
          lambda msg, **_: StoreMessage(msg)
      )
      mock_conn.outgoing.ListClients.side_effect = (
          lambda msg, **_: admin_pb2.ListClientsResponse()
      )

      Reset()
      func(*(args + (mock_conn,)), **kwargs)

  return Wrapper


def Reset():
  """Resets the test queue."""

  global _messages_by_client_id
  with _message_lock:
    _messages_by_client_id = {}
