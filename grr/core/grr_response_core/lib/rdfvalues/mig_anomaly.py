#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""

from grr_response_core.lib.rdfvalues import anomaly as rdf_anomaly
from grr_response_proto import anomaly_pb2


def ToProtoAnomaly(rdf: rdf_anomaly.Anomaly) -> anomaly_pb2.Anomaly:
  return rdf.AsPrimitiveProto()


def ToRDFAnomaly(proto: anomaly_pb2.Anomaly) -> rdf_anomaly.Anomaly:
  return rdf_anomaly.Anomaly.FromSerializedBytes(proto.SerializeToString())
