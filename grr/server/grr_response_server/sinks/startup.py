#!/usr/bin/env python
"""A module with the startup sink."""

from grr_response_server import data_store
from grr_response_server.sinks import abstract
from grr_response_proto import rrg_pb2
from grr_response_proto.rrg import startup_pb2 as rrg_startup_pb2


class StartupSink(abstract.Sink):
  """A sink that accepts startup notifications from the GRR agents."""

  def Accept(self, client_id: str, parcel: rrg_pb2.Parcel) -> None:
    startup = rrg_startup_pb2.Startup()
    startup.ParseFromString(parcel.payload.value)

    assert data_store.REL_DB is not None
    data_store.REL_DB.WriteClientRRGStartup(client_id, startup)
