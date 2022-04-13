#!/usr/bin/env python
"""A module with RDF values wrapping server osquery protobufs."""

from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import osquery_pb2


class OsqueryFlowArgs(rdf_structs.RDFProtoStruct):
  """An RDF wrapper class for the `OsqueryFlowArgs` proto."""

  protobuf = osquery_pb2.OsqueryFlowArgs
  rdf_deps = []

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)

    if not self.HasField("timeout_millis"):
      self.timeout_millis = 5 * 60 * 1000  # 5 minutes.


class OsqueryCollectedFile(rdf_structs.RDFProtoStruct):
  """An RDF wrapper class for the `OsqueryCollectedFile` proto."""

  protobuf = osquery_pb2.OsqueryCollectedFile
  rdf_deps = [rdf_client_fs.StatEntry]
