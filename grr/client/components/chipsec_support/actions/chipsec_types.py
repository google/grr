#!/usr/bin/env python
"""RDFValues used to communicate with Chipsec."""
__author__ = "tweksteen@gmail.com (Thiebaud Weksteen)"

import chipsec_pb2

from grr.lib.rdfvalues import structs as rdf_structs


class DumpFlashImageRequest(rdf_structs.RDFProtoStruct):
  """A request to Chipsec to dump the flash image (BIOS)."""
  protobuf = chipsec_pb2.DumpFlashImageRequest


class DumpFlashImageResponse(rdf_structs.RDFProtoStruct):
  """A response from Chipsec to dump the flash image (BIOS)."""
  protobuf = chipsec_pb2.DumpFlashImageResponse


class ACPITableData(rdf_structs.RDFProtoStruct):
  """Response from Chipsec for one ACPI table."""
  protobuf = chipsec_pb2.ACPITableData


class DumpACPITableRequest(rdf_structs.RDFProtoStruct):
  """A request to Chipsec to dump an ACPI table."""
  protobuf = chipsec_pb2.DumpACPITableRequest


class DumpACPITableResponse(rdf_structs.RDFProtoStruct):
  """A response from Chipsec to dump an ACPI table."""
  protobuf = chipsec_pb2.DumpACPITableResponse
