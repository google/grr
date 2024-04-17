#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""

from grr_response_core.lib.rdfvalues import events as rdf_events
from grr_response_proto import jobs_pb2


def ToProtoAuditEvent(rdf: rdf_events.AuditEvent) -> jobs_pb2.AuditEvent:
  return rdf.AsPrimitiveProto()


def ToRDFAuditEvent(proto: jobs_pb2.AuditEvent) -> rdf_events.AuditEvent:
  return rdf_events.AuditEvent.FromSerializedBytes(proto.SerializeToString())
