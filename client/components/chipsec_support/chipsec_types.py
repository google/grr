#!/usr/bin/env python
"""RDFValues used to communicate with Chipsec."""
__author__ = "tweksteen@gmail.com (Thiebaud Weksteen)"

# pylint: disable=g-import-not-at-top, g-statement-before-imports
try:
  import chipsec_pb2
except ImportError:
  from grr.client.components.chipsec_support import chipsec_pb2
# pylint: enable=g-import-not-at-top, g-statement-before-imports

from grr.lib.rdfvalues import structs as rdf_structs


class DumpFlashImageRequest(rdf_structs.RDFProtoStruct):
  """A request to Chipsec to dump the flash image (BIOS)."""
  protobuf = chipsec_pb2.DumpFlashImageRequest


class DumpFlashImageResponse(rdf_structs.RDFProtoStruct):
  """A response from Chipsec to dump the flash image (BIOS)."""
  protobuf = chipsec_pb2.DumpFlashImageResponse
