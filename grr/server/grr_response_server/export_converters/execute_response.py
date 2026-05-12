#!/usr/bin/env python
"""Classes for exporting ExecuteResponse."""

from collections.abc import Iterator

from grr_response_proto import export_pb2
from grr_response_proto import jobs_pb2
from grr_response_server.export_converters import base


class ExecuteResponseConverterProto(
    base.ExportConverterProto[jobs_pb2.ExecuteResponse]
):
  """Export converter for ExecuteResponse."""

  input_proto_type = jobs_pb2.ExecuteResponse
  output_proto_types = (export_pb2.ExportedExecuteResponse,)

  def Convert(
      self,
      metadata: export_pb2.ExportedMetadata,
      execute_response: jobs_pb2.ExecuteResponse,
  ) -> Iterator[export_pb2.ExportedExecuteResponse]:
    yield export_pb2.ExportedExecuteResponse(
        metadata=metadata,
        cmd=execute_response.request.cmd,
        args=" ".join(execute_response.request.args),
        exit_status=execute_response.exit_status,
        stdout=execute_response.stdout,
        stderr=execute_response.stderr,
        # `time_used` is int32 (for a reason unknown): to be on the safe
        # side, making sure it's not negative.
        time_used_us=max(0, execute_response.time_used),
    )
