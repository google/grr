#!/usr/bin/env python
"""API handlers for stats."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from future.utils import itervalues

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import stats as rdf_stats
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_core.stats import stats_collector_instance
from grr_response_proto.api import stats_pb2
from grr_response_server import stats_store
from grr_response_server import timeseries
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


class ApiListStatsStoreMetricsMetadataArgs(rdf_structs.RDFProtoStruct):
  protobuf = stats_pb2.ApiListStatsStoreMetricsMetadataArgs


class ApiListStatsStoreMetricsMetadataResult(rdf_structs.RDFProtoStruct):
  protobuf = stats_pb2.ApiListStatsStoreMetricsMetadataResult
  rdf_deps = [
      rdf_stats.MetricMetadata,
  ]


class ApiListStatsStoreMetricsMetadataHandler(
    api_call_handler_base.ApiCallHandler):
  """Renders available metrics descriptors for a given system component."""

  args_type = ApiListStatsStoreMetricsMetadataArgs
  result_type = ApiListStatsStoreMetricsMetadataResult

  def Handle(self, args, token=None):
    metric_metadata = stats_collector_instance.Get().GetAllMetricsMetadata()
    return ApiListStatsStoreMetricsMetadataResult(
        items=sorted(itervalues(metric_metadata), key=lambda m: m.varname))


class ApiGetStatsStoreMetricArgs(rdf_structs.RDFProtoStruct):
  protobuf = stats_pb2.ApiGetStatsStoreMetricArgs
  rdf_deps = [
      rdfvalue.Duration,
      rdfvalue.RDFDatetime,
  ]


class ApiGetStatsStoreMetricHandler(api_call_handler_base.ApiCallHandler):
  """Renders historical data for a given metric."""

  args_type = ApiGetStatsStoreMetricArgs
  result_type = ApiStatsStoreMetric

  def Handle(self, args, token):
    start_time = args.start
    end_time = args.end
    if not end_time:
      end_time = rdfvalue.RDFDatetime.Now()
    if not start_time:
      start_time = end_time - rdfvalue.Duration("1h")

    # Run for a little extra time at the start. This improves the quality of the
    # first data points of counter metrics which don't appear in every interval.
    base_start_time = start_time
    # pylint: disable=g-no-augmented-assignment
    start_time = start_time - rdfvalue.Duration("10m")
    # pylint: enable=g-no-augmented-assignment

    if end_time <= start_time:
      raise ValueError("End time can't be less than start time.")

    result = ApiStatsStoreMetric(
        start=base_start_time, end=end_time, metric_name=args.metric_name)

    data = stats_store.ReadStats(
        unicode(args.component.name.lower()),
        args.metric_name,
        time_range=(start_time, end_time),
        token=token)

    if not data:
      return result

    metric_metadata = stats_collector_instance.Get().GetMetricMetadata(
        args.metric_name)

    query = stats_store.StatsStoreDataQuery(data)
    query.In(args.component.name.lower() + ".*").In(args.metric_name)
    if metric_metadata.fields_defs:
      query.InAll()

    requested_duration = end_time - start_time
    if requested_duration >= rdfvalue.Duration("1d"):
      sampling_duration = rdfvalue.Duration("5m")
    elif requested_duration >= rdfvalue.Duration("6h"):
      sampling_duration = rdfvalue.Duration("1m")
    else:
      sampling_duration = rdfvalue.Duration("30s")

    if metric_metadata.metric_type == metric_metadata.MetricType.COUNTER:
      query.TakeValue().MakeIncreasing().Normalize(
          sampling_duration,
          start_time,
          end_time,
          mode=timeseries.NORMALIZE_MODE_COUNTER)
    elif metric_metadata.metric_type == metric_metadata.MetricType.EVENT:
      if args.distribution_handling_mode == "DH_SUM":
        query.TakeDistributionSum()
      elif args.distribution_handling_mode == "DH_COUNT":
        query.TakeDistributionCount()
      else:
        raise ValueError("Unexpected request.distribution_handling_mode "
                         "value: %s." % args.distribution_handling_mode)
      query.MakeIncreasing()
      query.Normalize(
          sampling_duration,
          start_time,
          end_time,
          mode=timeseries.NORMALIZE_MODE_COUNTER)

    elif metric_metadata.metric_type == metric_metadata.MetricType.GAUGE:
      query.TakeValue().Normalize(sampling_duration, start_time, end_time)
    else:
      raise RuntimeError("Unsupported metric type.")

    if args.aggregation_mode == "AGG_SUM":
      query.AggregateViaSum()
    elif args.aggregation_mode == "AGG_MEAN":
      query.AggregateViaMean()
    elif args.aggregation_mode == "AGG_NONE":
      pass
    else:
      raise ValueError(
          "Unexpected request.aggregation value: %s." % args.aggregation)

    if (args.rate and
        metric_metadata.metric_type != metric_metadata.MetricType.GAUGE):
      query.Rate()

    query.InTimeRange(base_start_time, end_time)

    for value, timestamp in query.ts.data:
      if value is not None:
        result.data_points.append(
            ApiStatsStoreMetricDataPoint(timestamp=timestamp, value=value))

    return result


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
