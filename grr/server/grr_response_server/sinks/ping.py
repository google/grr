#!/usr/bin/env python
"""A module with the ping sink."""

import random

from grr_response_proto import objects_pb2
from grr_response_server import data_store
from grr_response_server import foreman
from grr_response_server.sinks import abstract
from grr_response_proto import rrg_pb2
from grr_response_proto.rrg import ping_pb2 as rrg_ping_pb2


class PingSink(abstract.Sink):
  """A sink that accepts ping messages from GRR agents."""

  def Accept(self, client_id: str, parcel: rrg_pb2.Parcel) -> None:
    # At this time we do not do anything interesting with the ping message. We
    # still deserialize it but only to ensure its validity.
    ping = rrg_ping_pb2.Ping()
    ping.ParseFromString(parcel.payload.value)

    # We cannot call foreman directly here as sinks are processes on the front-
    # end and forman can start flows, including triggering the `Start` method.
    # By issuing a message handler request instead, we force it to be picked up
    # by the worker.

    # TODO: Instead of this, consider rewriting foreman to sche-
    # dule flows instead of starting them.

    request = objects_pb2.MessageHandlerRequest()
    request.client_id = client_id
    request.request_id = random.randrange(0, 2**64)
    request.handler_name = foreman.ForemanMessageHandler.handler_name

    assert data_store.REL_DB is not None
    data_store.REL_DB.WriteMessageHandlerRequests([request])
