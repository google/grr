#!/usr/bin/env python
"""A module for classes and functions related to sinks.

Sinks are "next generation" well-known flows (aka message handlers). They are
responsible for processing parcels (out-of-band messages) from the GRR agent.
They allow to bypass the usual communication between the flow and the agent to
avoid unnecessary processing of the messages on the worker or to send messages
that are not replies to a flow.

The "avoid unnecessary processing of messages" part is e.g. realized by the
blobs sink. If the agent sent file blobs as usual flow responses, first the GRR
frontend would have to process the response and put it into the database only
for the worker to pick it up and put it into a blobstore. Instead, the agent can
send a parcel to the blob sink that immediately puts the data to a blobstore.

The "send messages that are not replies" part is e.g. realized by the startup
sink. The GRR server would like to be notified of the startup of the agent but
if the agent is able to send only flow replies to the server there is no way to
do that. This is where the startup sink comes into play and allows the agent to
send information about its startup.
"""

from collections.abc import Mapping, Sequence

from grr_response_server.sinks import abstract
from grr_response_server.sinks import blob
from grr_response_server.sinks import ping
from grr_response_server.sinks import startup
from grr_response_proto import rrg_pb2

# Re-export for convenience.
Sink = abstract.Sink

# Registry of all known sinks.
REGISTRY: Mapping["rrg_pb2.Sink", abstract.Sink] = {
    rrg_pb2.Sink.STARTUP: startup.StartupSink(),
    rrg_pb2.Sink.BLOB: blob.BlobSink(),
    rrg_pb2.Sink.PING: ping.PingSink(),
}


class UnknownSinkError(Exception):
  """Error class for cases where the specified sink is not known."""

  sink: rrg_pb2.Sink

  def __init__(self, sink: rrg_pb2.Sink) -> None:
    super().__init__(f"Unknown sink '{sink}'")
    self.sink = sink


def Accept(client_id: str, parcel: rrg_pb2.Parcel) -> None:
  """Processes the given parcel on an appropriate sink.

  Args:
    client_id: An identifier of the client from which the message came.
    parcel: A parcel to process.

  Raises:
    UnknownSinkError: If the sink for which the parcel is addressed isn't known.
  """
  try:
    sink = REGISTRY[parcel.sink]
  except KeyError as error:
    raise UnknownSinkError(parcel.sink) from error

  sink.Accept(client_id, parcel)


def AcceptMany(client_id: str, parcels: Sequence[rrg_pb2.Parcel]) -> None:
  """Processes given parcels on appropriate sinks.

  Args:
    client_id: An identifier of the client from which the message came.
    parcels: Parcels to process.

  Raises:
    UnknownSinkError: If the sink for which the parcel is addressed isn't known.
  """
  parcels_by_sink: dict[Sink, list[rrg_pb2.Parcel]] = {}

  for parcel in parcels:
    try:
      sink = REGISTRY[parcel.sink]
    except KeyError as error:
      raise UnknownSinkError(parcel.sink) from error

    parcels_by_sink.setdefault(sink, []).append(parcel)

  for sink, sink_parcels in parcels_by_sink.items():
    sink.AcceptMany(client_id, sink_parcels)
