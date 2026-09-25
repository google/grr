#!/usr/bin/env python
"""A module with the abort sink."""

from grr_response_proto import flows_pb2
from grr_response_server import flow_base
from grr_response_server.databases import db_utils
from grr_response_server.sinks import abstract
from grr_response_proto import rrg_pb2
from grr_response_proto.rrg import abort_pb2 as rrg_abort_pb2


class AbortSink(abstract.Sink):
  """A sink that accepts abort notifications from the GRR agents."""

  def Accept(self, client_id: str, parcel: rrg_pb2.Parcel) -> None:
    abort = rrg_abort_pb2.Abort()
    abort.ParseFromString(parcel.payload.value)

    flow_base.TerminateFlow(
        client_id=client_id,
        flow_id=db_utils.IntToFlowID(abort.flow_id),
        reason=f"Agent aborted during processing of request {abort.request_id}",
        flow_state=flows_pb2.Flow.CRASHED,
    )
