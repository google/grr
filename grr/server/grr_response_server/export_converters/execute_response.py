#!/usr/bin/env python
"""Classes for exporting ExecuteResponse."""

from typing import Iterator

from grr_response_core.lib.rdfvalues import client_action as rdf_client_action
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import export_pb2
from grr_response_server.export_converters import base


class ExportedExecuteResponse(rdf_structs.RDFProtoStruct):
  protobuf = export_pb2.ExportedExecuteResponse
  rdf_deps = [base.ExportedMetadata]


class ExecuteResponseConverter(base.ExportConverter):
  """Export converter for ExecuteResponse."""

  input_rdf_type = rdf_client_action.ExecuteResponse

  def Convert(
      self,
      metadata: base.ExportedMetadata,
      r: rdf_client_action.ExecuteResponse,
  ) -> Iterator[ExportedExecuteResponse]:
    yield ExportedExecuteResponse(
        metadata=metadata,
        cmd=r.request.cmd,
        args=" ".join(r.request.args),
        exit_status=r.exit_status,
        stdout=r.stdout,
        stderr=r.stderr,
        # ExecuteResponse is uint32 (for a reason unknown): to be on the safe
        # side, making sure it's not negative.
        time_used_us=max(0, r.time_used),
    )
