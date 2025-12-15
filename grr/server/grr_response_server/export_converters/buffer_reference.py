#!/usr/bin/env python
"""Classes for exporting BufferReference."""

from collections.abc import Iterator

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import mig_paths
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import export_pb2
from grr_response_proto import jobs_pb2
from grr_response_server.export_converters import base


class ExportedMatch(rdf_structs.RDFProtoStruct):
  protobuf = export_pb2.ExportedMatch
  rdf_deps = [
      base.ExportedMetadata,
      rdfvalue.RDFURN,
  ]


class BufferReferenceToExportedMatchConverter(base.ExportConverter):
  """Export converter for BufferReference instances."""

  input_rdf_type = rdf_client.BufferReference

  def Convert(
      self,
      metadata: base.ExportedMetadata,
      buffer_reference: rdf_client.BufferReference,
  ) -> Iterator[ExportedMatch]:
    yield ExportedMatch(
        metadata=metadata,
        offset=buffer_reference.offset,
        length=buffer_reference.length,
        data=buffer_reference.data,
        urn=buffer_reference.pathspec.AFF4Path(metadata.client_urn),
    )


class BufferReferenceToExportedMatchConverterProto(
    base.ExportConverterProto[jobs_pb2.BufferReference]
):
  """Export converter for BufferReference instances."""

  input_proto_type = jobs_pb2.BufferReference
  output_proto_types = (export_pb2.ExportedMatch,)

  def Convert(
      self,
      metadata: export_pb2.ExportedMetadata,
      buffer_reference: jobs_pb2.BufferReference,
  ) -> Iterator[export_pb2.ExportedMatch]:
    rdf_pathspec = mig_paths.ToRDFPathSpec(buffer_reference.pathspec)
    client_urn = rdfvalue.RDFURN(metadata.client_urn)
    path_urn = rdf_pathspec.AFF4Path(client_urn)
    yield export_pb2.ExportedMatch(
        metadata=metadata,
        offset=buffer_reference.offset,
        length=buffer_reference.length,
        data=buffer_reference.data,
        urn=path_urn.SerializeToWireFormat(),
    )
