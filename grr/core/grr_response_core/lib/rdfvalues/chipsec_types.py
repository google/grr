#!/usr/bin/env python
"""RDFValues used to communicate with Chipsec."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import structs as rdf_structs

from grr_response_proto import chipsec_pb2


class DumpFlashImageRequest(rdf_structs.RDFProtoStruct):
  """A request to Chipsec to dump the flash image (BIOS)."""
  protobuf = chipsec_pb2.DumpFlashImageRequest


class DumpFlashImageResponse(rdf_structs.RDFProtoStruct):
  """A response from Chipsec to dump the flash image (BIOS)."""
  protobuf = chipsec_pb2.DumpFlashImageResponse
  rdf_deps = [
      rdf_paths.PathSpec,
  ]


class ACPITableData(rdf_structs.RDFProtoStruct):
  """Response from Chipsec for one ACPI table."""
  protobuf = chipsec_pb2.ACPITableData
  rdf_deps = [
      rdfvalue.RDFBytes,
  ]


class DumpACPITableRequest(rdf_structs.RDFProtoStruct):
  """A request to Chipsec to dump an ACPI table."""
  protobuf = chipsec_pb2.DumpACPITableRequest


class DumpACPITableResponse(rdf_structs.RDFProtoStruct):
  """A response from Chipsec to dump an ACPI table."""
  protobuf = chipsec_pb2.DumpACPITableResponse
  rdf_deps = [
      ACPITableData,
  ]
