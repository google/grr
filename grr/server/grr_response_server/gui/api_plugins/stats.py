#!/usr/bin/env python
"""API handlers for stats."""

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_core.stats import stats_collector_instance
from grr_response_proto.api import stats_pb2
from grr_response_server.gui import admin_ui_metrics
from grr_response_server.gui import api_call_handler_base
from grr_response_server.gui.api_plugins.report_plugins import rdf_report_plugins
from grr_response_server.gui.api_plugins.report_plugins import report_plugins


class ApiListReportsResult(rdf_structs.RDFProtoStruct):
  protobuf = stats_pb2.ApiListReportsResult
  rdf_deps = [
      rdf_report_plugins.ApiReport,
  ]


class ApiListReportsHandler(api_call_handler_base.ApiCallHandler):
  """Lists the reports."""

  result_type = ApiListReportsResult

  def Handle(self, args, context):
    return ApiListReportsResult(
        reports=sorted(
            (
                rdf_report_plugins.ApiReport(
                    desc=report_cls.GetReportDescriptor(), data=None
                )
                for report_cls in report_plugins.GetAvailableReportPlugins()
            ),
            key=lambda report: (report.desc.type, report.desc.title),
        )
    )


class ApiGetReportArgs(rdf_structs.RDFProtoStruct):
  protobuf = stats_pb2.ApiGetReportArgs
  rdf_deps = [
      rdfvalue.DurationSeconds,
      rdfvalue.RDFDatetime,
  ]


class ApiGetReportHandler(api_call_handler_base.ApiCallHandler):
  """Fetches data for the given report."""

  args_type = ApiGetReportArgs
  result_type = rdf_report_plugins.ApiReport

  def Handle(self, args, context):
    report = report_plugins.GetReportByName(args.name)

    if not args.client_label:
      args.client_label = "All"

    return rdf_report_plugins.ApiReport(
        desc=report.GetReportDescriptor(), data=report.GetReportData(args)
    )


class FieldValue(rdf_structs.RDFProtoStruct):
  protobuf = stats_pb2.FieldValue


class ApiIncrementCounterMetricArgs(rdf_structs.RDFProtoStruct):
  protobuf = stats_pb2.ApiIncrementCounterMetricArgs
  rdf_deps = [
      FieldValue,
  ]


class ApiIncrementCounterMetricResult(rdf_structs.RDFProtoStruct):
  protobuf = stats_pb2.ApiIncrementCounterMetricResult


class ApiIncrementCounterMetricHandler(api_call_handler_base.ApiCallHandler):
  """Fetches data for the given report."""

  args_type = ApiIncrementCounterMetricArgs
  result_type = ApiIncrementCounterMetricResult

  def Handle(self, args, context):
    if not args.metric_name:
      raise ValueError("Missing `metric_name` input (must be provided).")

    if args.metric_name not in admin_ui_metrics.API_INCREASE_ALLOWLIST:
      raise ValueError(
          f"Cannot increase {args.metric_name}. It is not allowlisted in"
          f" {admin_ui_metrics.API_INCREASE_ALLOWLIST}"
      )

    fields = []
    for value in args.field_values:
      if value.field_type == stats_pb2.FieldValue.STRING:
        fields.append(value.string_value)
      elif value.field_type == stats_pb2.FieldValue.NUMBER:
        fields.append(value.number_value)
      else:
        raise ValueError(
            f"Bad field value type {value.field_type} must be STRING or NUMBER."
            f" All field values: {args.field_values}"
        )

    stats_collector_instance.Get().IncrementCounter(
        args.metric_name, fields=fields
    )

    return ApiIncrementCounterMetricResult()
