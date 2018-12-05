#!/usr/bin/env python
"""UI reports related rdfvalues."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib.rdfvalues import events as rdf_events
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto.api import stats_pb2


class ApiReportDescriptor(rdf_structs.RDFProtoStruct):
  protobuf = stats_pb2.ApiReportDescriptor


class ApiReportDataPoint1D(rdf_structs.RDFProtoStruct):
  protobuf = stats_pb2.ApiReportDataPoint1D


class ApiReportDataPoint2D(rdf_structs.RDFProtoStruct):
  protobuf = stats_pb2.ApiReportDataPoint2D


class ApiReportDataSeries2D(rdf_structs.RDFProtoStruct):
  protobuf = stats_pb2.ApiReportDataSeries2D
  rdf_deps = [
      ApiReportDataPoint2D,
  ]


class ApiReportTickSpecifier(rdf_structs.RDFProtoStruct):
  protobuf = stats_pb2.ApiReportTickSpecifier


class ApiStackChartReportData(rdf_structs.RDFProtoStruct):
  protobuf = stats_pb2.ApiStackChartReportData
  rdf_deps = [
      ApiReportDataSeries2D,
      ApiReportTickSpecifier,
  ]


class ApiPieChartReportData(rdf_structs.RDFProtoStruct):
  protobuf = stats_pb2.ApiPieChartReportData
  rdf_deps = [
      ApiReportDataPoint1D,
  ]


class ApiLineChartReportData(rdf_structs.RDFProtoStruct):
  protobuf = stats_pb2.ApiLineChartReportData
  rdf_deps = [
      ApiReportDataSeries2D,
  ]


class ApiAuditChartReportData(rdf_structs.RDFProtoStruct):
  protobuf = stats_pb2.ApiAuditChartReportData
  rdf_deps = [
      rdf_events.AuditEvent,
  ]


class ApiReportData(rdf_structs.RDFProtoStruct):
  protobuf = stats_pb2.ApiReportData
  rdf_deps = [
      ApiAuditChartReportData,
      ApiLineChartReportData,
      ApiPieChartReportData,
      ApiStackChartReportData,
  ]


class ApiReport(rdf_structs.RDFProtoStruct):
  protobuf = stats_pb2.ApiReport
  rdf_deps = [
      ApiReportData,
      ApiReportDescriptor,
  ]
