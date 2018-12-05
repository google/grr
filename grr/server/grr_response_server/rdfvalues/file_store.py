#!/usr/bin/env python
"""FileStore implementation-related RDFValues."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import file_store_pb2
from grr_response_server.rdfvalues import objects as rdf_objects


class FileStoreAddEvent(rdf_structs.RDFProtoStruct):
  """Basic metadata about a path which has been observed on a client."""
  protobuf = file_store_pb2.FileStoreAddEvent
  rdf_deps = [
      rdf_objects.SHA256HashID,
      rdf_objects.BlobID,
  ]
