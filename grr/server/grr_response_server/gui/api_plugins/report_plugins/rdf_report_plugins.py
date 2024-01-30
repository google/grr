#!/usr/bin/env python
"""UI reports related rdfvalues."""

from grr_response_core.lib.rdfvalues import events as rdf_events
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto.api import stats_pb2


class ApiReportDescriptor(rdf_structs.RDFProtoStruct):
  protobuf = stats_pb2.ApiReportDescriptor


class ApiAuditChartReportData(rdf_structs.RDFProtoStruct):
  protobuf = stats_pb2.ApiAuditChartReportData
  rdf_deps = [
      rdf_events.AuditEvent,
  ]


class ApiReportData(rdf_structs.RDFProtoStruct):
  protobuf = stats_pb2.ApiReportData
  rdf_deps = [
      ApiAuditChartReportData,
  ]


class ApiReport(rdf_structs.RDFProtoStruct):
  protobuf = stats_pb2.ApiReport
  rdf_deps = [
      ApiReportData,
      ApiReportDescriptor,
  ]
