#!/usr/bin/env python
"""API handlers for stats."""

from grr.gui import api_call_handler_base
from grr.gui.api_plugins.report_plugins import report_plugins
from grr.lib import aff4
from grr.lib import rdfvalue
from grr.lib import timeseries
from grr.lib import utils
from grr.lib.aff4_objects import stats_store as stats_store_lib
from grr.lib.rdfvalues import structs as rdf_structs

from grr.proto import api_pb2


class ApiStatsStoreMetric(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiStatsStoreMetric


class ApiStatsStoreMetricDataPoint(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiStatsStoreMetricDataPoint


class ApiListStatsStoreMetricsMetadataArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiListStatsStoreMetricsMetadataArgs


class ApiListStatsStoreMetricsMetadataResult(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiListStatsStoreMetricsMetadataResult


class ApiListStatsStoreMetricsMetadataHandler(
    api_call_handler_base.ApiCallHandler):
  """Renders available metrics descriptors for a given system component."""

  args_type = ApiListStatsStoreMetricsMetadataArgs
  result_type = ApiListStatsStoreMetricsMetadataResult

  def Handle(self, args, token=None):
    stats_store = aff4.FACTORY.Create(
        None, aff4_type=stats_store_lib.StatsStore, mode="w", token=token)

    process_ids = [pid for pid in stats_store.ListUsedProcessIds()
                   if pid.startswith(args.component.name.lower())]

    result = ApiListStatsStoreMetricsMetadataResult()
    if not process_ids:
      return result
    else:
      metadata = stats_store.ReadMetadata(process_id=process_ids[0])
      result.items = sorted(metadata.metrics, key=lambda m: m.varname)
      return result


class ApiGetStatsStoreMetricArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiGetStatsStoreMetricArgs


class ApiGetStatsStoreMetricHandler(api_call_handler_base.ApiCallHandler):
  """Renders historical data for a given metric."""

  args_type = ApiGetStatsStoreMetricArgs
  result_type = ApiStatsStoreMetric

  def Handle(self, args, token):
    stats_store = aff4.FACTORY.Create(
        stats_store_lib.StatsStore.DATA_STORE_ROOT,
        aff4_type=stats_store_lib.StatsStore,
        mode="rw",
        token=token)

    process_ids = stats_store.ListUsedProcessIds()
    filtered_ids = [pid for pid in process_ids
                    if pid.startswith(args.component.name.lower())]

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

    data = stats_store.MultiReadStats(
        process_ids=filtered_ids,
        metric_name=utils.SmartStr(args.metric_name),
        timestamp=(start_time, end_time))

    if not data:
      return result

    pid = data.keys()[0]
    metadata = stats_store.ReadMetadata(process_id=pid)
    metric_metadata = metadata.AsDict()[args.metric_name]

    query = stats_store_lib.StatsStoreDataQuery(data)
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
      raise ValueError("Unexpected request.aggregation value: %s." %
                       args.aggregation)

    if (args.rate and
        metric_metadata.metric_type != metric_metadata.MetricType.GAUGE):
      query.Rate()

    query.InTimeRange(base_start_time, end_time)

    for value, timestamp in query.ts.data:
      if value is not None:
        result.data_points.append(
            ApiStatsStoreMetricDataPoint(
                timestamp=timestamp, value=value))

    return result


class ApiListReportsResult(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiListReportsResult


class ApiListReportsHandler(api_call_handler_base.ApiCallHandler):
  """Lists the reports."""

  result_type = ApiListReportsResult

  def Handle(self, args, token):
    return ApiListReportsResult(reports=[
        report_plugins.ApiReport(
            desc=report_cls.GetReportDescriptor(), data=None)
        for report_cls in report_plugins.GetAvailableReportPlugins()
    ])


class ApiGetReportArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiGetReportArgs


class ApiGetReportHandler(api_call_handler_base.ApiCallHandler):
  """Fetches data for the given report."""

  args_type = ApiGetReportArgs
  result_type = report_plugins.ApiReport

  def Handle(self, args, token):
    report = report_plugins.GetReportByName(args.name)

    return report_plugins.ApiReport(
        desc=report.GetReportDescriptor(),
        data=report.GetReportData(args, token))
