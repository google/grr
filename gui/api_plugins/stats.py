#!/usr/bin/env python
"""API renderers for stats."""

import re

from grr.gui import api_call_renderers
from grr.gui import api_value_renderers

from grr.lib import aff4
from grr.lib import rdfvalue
from grr.lib import registry
from grr.lib import utils
from grr.lib.aff4_objects import stats_store as stats_store_lib

from grr.proto import api_pb2


class ApiStatsStoreMetricsMetadataRendererArgs(rdfvalue.RDFProtoStruct):
  protobuf = api_pb2.ApiStatsStoreMetricsMetadataRendererArgs


class ApiStatsStoreMetricsMetadataRenderer(api_call_renderers.ApiCallRenderer):
  """Renders available metrics descriptors for a given system component."""

  args_type = ApiStatsStoreMetricsMetadataRendererArgs

  def Render(self, args, token=None):
    stats_store = aff4.FACTORY.Create(None, aff4_type="StatsStore",
                                      mode="w", token=token)

    process_ids = [pid for pid in stats_store.ListUsedProcessIds()
                   if pid.startswith(args.component.name.lower())]
    if not process_ids:
      return {}
    else:
      metadata = stats_store.ReadMetadata(process_id=process_ids[0])
      return api_value_renderers.RenderValue(metadata)


class ApiStatsStoreMetricRendererArgs(rdfvalue.RDFProtoStruct):
  protobuf = api_pb2.ApiStatsStoreMetricRendererArgs


class ApiStatsStoreMetricRenderer(api_call_renderers.ApiCallRenderer):
  """Renders historical data for a given metric."""

  args_type = ApiStatsStoreMetricRendererArgs

  def Render(self, args, token):
    stats_store = aff4.FACTORY.Create(
        stats_store_lib.StatsStore.DATA_STORE_ROOT,
        aff4_type="StatsStore", mode="rw", token=token)

    process_ids = stats_store.ListUsedProcessIds()
    filtered_ids = [pid for pid in process_ids
                    if pid.startswith(args.component.name.lower())]

    start_time = args.start
    end_time = args.end

    if not end_time:
      end_time = rdfvalue.RDFDatetime().Now()

    if not start_time:
      start_time = end_time - rdfvalue.Duration("1h")

    if end_time <= start_time:
      raise ValueError("End time can't be less than start time.")

    result = dict(
        start=start_time.AsMicroSecondsFromEpoch(),
        end=end_time.AsMicroSecondsFromEpoch(),
        metric_name=args.metric_name,
        timeseries=[])

    data = stats_store.MultiReadStats(
        process_ids=filtered_ids,
        predicate_regex=re.escape(utils.SmartStr(args.metric_name)),
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
      query.TakeValue().EnsureIsIncremental().Resample(sampling_duration)
      query.FillMissing(rdfvalue.Duration("10m"))
    elif metric_metadata.metric_type == metric_metadata.MetricType.EVENT:
      if args.distribution_handling_mode == "DH_SUM":
        query.TakeDistributionSum()
      elif args.distribution_handling_mode == "DH_COUNT":
        query.TakeDistributionCount()
      else:
        raise ValueError("Unexpected request.distribution_handling_mode "
                         "value: %s." % args.distribution_handling_mode)

      query.EnsureIsIncremental().Resample(sampling_duration)
      query.FillMissing(rdfvalue.Duration("10m"))
    elif metric_metadata.metric_type == metric_metadata.MetricType.GAUGE:
      query.TakeValue().Resample(sampling_duration)
      query.FillMissing(rdfvalue.Duration("10m"))
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
      query.Rate(args.rate)

    timeseries = []
    for timestamp, value in query.ts.iteritems():
      timeseries.append((timestamp.value / 1e6, value))

    result["timeseries"] = timeseries
    return result


class ApiStatsInitHook(registry.InitHook):

  def RunOnce(self):
    api_call_renderers.RegisterHttpRouteHandler(
        "GET", "/api/stats/store/<component>/metadata",
        ApiStatsStoreMetricsMetadataRenderer)
    api_call_renderers.RegisterHttpRouteHandler(
        "GET", "/api/stats/store/<component>/metrics/<metric_name>",
        ApiStatsStoreMetricRenderer)
