#!/usr/bin/env python
"""API handlers for stats."""

from grr.gui import api_call_handler_base
from grr.gui import api_value_renderers

from grr.lib import aff4
from grr.lib import rdfvalue
from grr.lib import timeseries
from grr.lib import utils
from grr.lib.aff4_objects import stats_store as stats_store_lib
from grr.lib.rdfvalues import structs as rdf_structs

from grr.proto import api_pb2

CATEGORY = "Other"


class ApiListStatsStoreMetricsMetadataArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiListStatsStoreMetricsMetadataArgs


class ApiListStatsStoreMetricsMetadataHandler(
    api_call_handler_base.ApiCallHandler):
  """Renders available metrics descriptors for a given system component."""

  category = CATEGORY
  args_type = ApiListStatsStoreMetricsMetadataArgs

  def Render(self, args, token=None):
    stats_store = aff4.FACTORY.Create(None,
                                      aff4_type=stats_store_lib.StatsStore,
                                      mode="w",
                                      token=token)

    process_ids = [pid for pid in stats_store.ListUsedProcessIds()
                   if pid.startswith(args.component.name.lower())]
    if not process_ids:
      return {}
    else:
      metadata = stats_store.ReadMetadata(process_id=process_ids[0])
      return api_value_renderers.RenderValue(metadata)


class ApiGetStatsStoreMetricArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiGetStatsStoreMetricArgs


class ApiGetStatsStoreMetricHandler(api_call_handler_base.ApiCallHandler):
  """Renders historical data for a given metric."""

  category = CATEGORY
  args_type = ApiGetStatsStoreMetricArgs

  def Render(self, args, token):
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
      end_time = rdfvalue.RDFDatetime().Now()

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

    result = dict(start=base_start_time.AsMicroSecondsFromEpoch(),
                  end=end_time.AsMicroSecondsFromEpoch(),
                  metric_name=args.metric_name,
                  timeseries=[])

    data = stats_store.MultiReadStats(
        process_ids=filtered_ids,
        metric_name=utils.SmartStr(args.metric_name),
        timestamp=(start_time, end_time))

    if not data:
      return result

    pid = data.keys()[0]
    metadata = stats_store.ReadMetadata(process_id=pid)
    metric_metadata = metadata[args.metric_name]

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
      query.Normalize(sampling_duration,
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

    ts = []
    for value, timestamp in query.ts.data:
      if value is not None:
        ts.append((timestamp / 1e3, value))

    result["timeseries"] = ts
    return result
