#!/usr/bin/env python
"""API handlers for stats."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto.api import stats_pb2
from grr_response_server.gui import api_call_handler_base
from grr_response_server.gui.api_plugins.report_plugins import rdf_report_plugins
from grr_response_server.gui.api_plugins.report_plugins import report_plugins


class ApiStatsStoreMetricDataPoint(rdf_structs.RDFProtoStruct):
  protobuf = stats_pb2.ApiStatsStoreMetricDataPoint
  rdf_deps = [
      rdfvalue.RDFDatetime,
  ]


class ApiStatsStoreMetric(rdf_structs.RDFProtoStruct):
  protobuf = stats_pb2.ApiStatsStoreMetric
  rdf_deps = [
      ApiStatsStoreMetricDataPoint,
      rdfvalue.RDFDatetime,
  ]


class ApiListReportsResult(rdf_structs.RDFProtoStruct):
  protobuf = stats_pb2.ApiListReportsResult
  rdf_deps = [
      rdf_report_plugins.ApiReport,
  ]


class ApiListReportsHandler(api_call_handler_base.ApiCallHandler):
  """Lists the reports."""

  result_type = ApiListReportsResult

  def Handle(self, args, token):
    return ApiListReportsResult(reports=sorted(
        (rdf_report_plugins.ApiReport(
            desc=report_cls.GetReportDescriptor(), data=None)
         for report_cls in report_plugins.GetAvailableReportPlugins()),
        key=lambda report: (report.desc.type, report.desc.title)))


class ApiGetReportArgs(rdf_structs.RDFProtoStruct):
  protobuf = stats_pb2.ApiGetReportArgs
  rdf_deps = [
      rdfvalue.Duration,
      rdfvalue.RDFDatetime,
  ]


class ApiGetReportHandler(api_call_handler_base.ApiCallHandler):
  """Fetches data for the given report."""

  args_type = ApiGetReportArgs
  result_type = rdf_report_plugins.ApiReport

  def Handle(self, args, token):
    report = report_plugins.GetReportByName(args.name)

    if not args.client_label:
      args.client_label = "All"

    return rdf_report_plugins.ApiReport(
        desc=report.GetReportDescriptor(),
        data=report.GetReportData(args, token))
