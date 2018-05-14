#!/usr/bin/env python
"""RDF values related to events."""

from grr.lib import rdfvalue
from grr.lib import utils
from grr.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import jobs_pb2


class AuditEvent(rdf_structs.RDFProtoStruct):
  """An RDF wrapper for the `AuditEvent` protobuf."""

  protobuf = jobs_pb2.AuditEvent
  rdf_deps = [
      rdfvalue.RDFDatetime,
      rdfvalue.RDFURN,
  ]

  def __init__(self, initializer=None, age=None, **kwargs):
    super(AuditEvent, self).__init__(initializer=initializer, age=age, **kwargs)
    if not self.id:
      self.id = utils.PRNG.GetUInt32()
    if not self.timestamp:
      self.timestamp = rdfvalue.RDFDatetime.Now()
