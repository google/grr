#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""

from grr_response_proto.api import stats_pb2
from grr_response_server.gui.api_plugins.report_plugins import rdf_report_plugins


def ToProtoApiReportDescriptor(
    rdf: rdf_report_plugins.ApiReportDescriptor,
) -> stats_pb2.ApiReportDescriptor:
  return rdf.AsPrimitiveProto()


def ToRDFApiReportDescriptor(
    proto: stats_pb2.ApiReportDescriptor,
) -> rdf_report_plugins.ApiReportDescriptor:
  return rdf_report_plugins.ApiReportDescriptor.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiAuditChartReportData(
    rdf: rdf_report_plugins.ApiAuditChartReportData,
) -> stats_pb2.ApiAuditChartReportData:
  return rdf.AsPrimitiveProto()


def ToRDFApiAuditChartReportData(
    proto: stats_pb2.ApiAuditChartReportData,
) -> rdf_report_plugins.ApiAuditChartReportData:
  return rdf_report_plugins.ApiAuditChartReportData.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiReportData(
    rdf: rdf_report_plugins.ApiReportData,
) -> stats_pb2.ApiReportData:
  return rdf.AsPrimitiveProto()


def ToRDFApiReportData(
    proto: stats_pb2.ApiReportData,
) -> rdf_report_plugins.ApiReportData:
  return rdf_report_plugins.ApiReportData.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiReport(rdf: rdf_report_plugins.ApiReport) -> stats_pb2.ApiReport:
  return rdf.AsPrimitiveProto()


def ToRDFApiReport(proto: stats_pb2.ApiReport) -> rdf_report_plugins.ApiReport:
  return rdf_report_plugins.ApiReport.FromSerializedBytes(
      proto.SerializeToString()
  )
