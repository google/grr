#!/usr/bin/env python
"""DO NOT USE. Deprecated RDFValues."""

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import jobs_pb2


class CpuSample(rdf_structs.RDFProtoStruct):
  """A single CPU sample."""

  protobuf = jobs_pb2.CpuSample
  rdf_deps = [
      rdfvalue.RDFDatetime,
  ]


class IOSample(rdf_structs.RDFProtoStruct):
  """A single I/O sample as collected by `psutil`."""

  protobuf = jobs_pb2.IOSample
  rdf_deps = [
      rdfvalue.RDFDatetime,
  ]


class ClientStats(rdf_structs.RDFProtoStruct):
  """A client stat object."""

  protobuf = jobs_pb2.ClientStats
  rdf_deps = [
      CpuSample,
      IOSample,
      rdfvalue.RDFDatetime,
  ]
