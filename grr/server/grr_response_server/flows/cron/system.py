#!/usr/bin/env python
# Lint as: python3
"""These flows are system-specific GRR cron flows."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import collections


from grr_response_core import config
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import stats as rdf_stats
from grr_response_core.lib.util import compatibility
from grr_response_server import client_report_utils
from grr_response_server import cronjobs
from grr_response_server import data_store
from grr_response_server import hunt
from grr_response_server.databases import db
from grr_response_server.flows.general import discovery as flows_discovery

# Maximum number of old stats entries to delete in a single db call.
_STATS_DELETION_BATCH_SIZE = 10000

# How often to save progress to the DB when deleting stats.
_stats_checkpoint_period = rdfvalue.Duration.From(15, rdfvalue.MINUTES)

# Label used for aggregating fleet statistics across all clients.
_ALL_CLIENT_FLEET_STATS_LABEL = "All"

_GENERAL_FLEET_STATS_DAY_BUCKETS = frozenset([1, 2, 3, 7, 14, 30, 60])

_FLEET_BREAKDOWN_DAY_BUCKETS = frozenset([1, 7, 14, 30])


def _WriteFleetBreakdownStatsToDB(fleet_stats, report_type):
  """Saves a snapshot of client activity stats to the DB.

  Args:
    fleet_stats: Client activity stats returned by the DB.
    report_type: rdf_stats.ClientGraphSeries.ReportType for the client stats.
  """
  graph_series_by_label = collections.defaultdict(
      lambda: rdf_stats.ClientGraphSeries(report_type=report_type))
  for day_bucket in fleet_stats.GetDayBuckets():
    for client_label in fleet_stats.GetAllLabels():
      graph = rdf_stats.Graph(title="%d day actives for %s label" %
                              (day_bucket, client_label))
      values = fleet_stats.GetValuesForDayAndLabel(day_bucket, client_label)
      for category_value, num_actives in sorted(values.items()):
        graph.Append(label=category_value, y_value=num_actives)
      graph_series_by_label[client_label].graphs.Append(graph)

  # Generate aggregate graphs for all clients in the snapshot (total for
  # every category_value regardless of label).
  for day_bucket in fleet_stats.GetDayBuckets():
    graph = rdf_stats.Graph(title="%d day actives for %s label" %
                            (day_bucket, _ALL_CLIENT_FLEET_STATS_LABEL))
    totals = fleet_stats.GetTotalsForDay(day_bucket)
    for category_value, num_actives in sorted(totals.items()):
      graph.Append(label=category_value, y_value=num_actives)
    graph_series_by_label[_ALL_CLIENT_FLEET_STATS_LABEL].graphs.Append(graph)

  for client_label, graph_series in graph_series_by_label.items():
    client_report_utils.WriteGraphSeries(graph_series, client_label)


class GRRVersionBreakDownCronJob(cronjobs.SystemCronJobBase):
  """Saves a snapshot of n-day-active stats for all GRR client versions."""

  frequency = rdfvalue.Duration.From(6, rdfvalue.HOURS)
  lifetime = rdfvalue.Duration.From(6, rdfvalue.HOURS)

  def Run(self):
    version_stats = data_store.REL_DB.CountClientVersionStringsByLabel(
        _FLEET_BREAKDOWN_DAY_BUCKETS)
    _WriteFleetBreakdownStatsToDB(
        version_stats, rdf_stats.ClientGraphSeries.ReportType.GRR_VERSION)


class OSBreakDownCronJob(cronjobs.SystemCronJobBase):
  """Saves a snapshot of n-day-active stats for all client platform/releases."""

  frequency = rdfvalue.Duration.From(1, rdfvalue.DAYS)
  lifetime = rdfvalue.Duration.From(20, rdfvalue.HOURS)

  def Run(self):
    platform_stats = data_store.REL_DB.CountClientPlatformsByLabel(
        _FLEET_BREAKDOWN_DAY_BUCKETS)
    _WriteFleetBreakdownStatsToDB(
        platform_stats, rdf_stats.ClientGraphSeries.ReportType.OS_TYPE)
    release_stats = data_store.REL_DB.CountClientPlatformReleasesByLabel(
        _FLEET_BREAKDOWN_DAY_BUCKETS)
    _WriteFleetBreakdownStatsToDB(
        release_stats, rdf_stats.ClientGraphSeries.ReportType.OS_RELEASE)


def _WriteFleetAggregateStatsToDB(client_label, bucket_dict):
  graph = rdf_stats.Graph()
  for day_bucket, num_actives in sorted(bucket_dict.items()):
    graph.Append(
        x_value=rdfvalue.Duration.From(day_bucket, rdfvalue.DAYS).microseconds,
        y_value=num_actives)
  graph_series = rdf_stats.ClientGraphSeries(
      report_type=rdf_stats.ClientGraphSeries.ReportType.N_DAY_ACTIVE)
  graph_series.graphs.Append(graph)
  client_report_utils.WriteGraphSeries(graph_series, client_label)


class LastAccessStatsCronJob(cronjobs.SystemCronJobBase):
  """Saves a snapshot of generalized n-day-active stats."""

  frequency = rdfvalue.Duration.From(1, rdfvalue.DAYS)
  lifetime = rdfvalue.Duration.From(20, rdfvalue.HOURS)

  def Run(self):
    platform_stats = data_store.REL_DB.CountClientPlatformsByLabel(
        _GENERAL_FLEET_STATS_DAY_BUCKETS)
    counts = platform_stats.GetAggregatedLabelCounts()
    for client_label, bucket_dict in counts.items():
      _WriteFleetAggregateStatsToDB(client_label, bucket_dict)
    _WriteFleetAggregateStatsToDB(_ALL_CLIENT_FLEET_STATS_LABEL,
                                  platform_stats.GetAggregatedTotalCounts())


class _ActiveCounter(object):
  """Helper class to count the number of times a specific category occurred.

  This class maintains running counts of event occurrence at different
  times. For example, the number of times an OS was reported as a category of
  "Windows" in the last 1 day, 7 days etc (as a measure of 7 day active windows
  systems).
  """

  active_days = [1, 7, 14, 30]

  def __init__(self, report_type):
    """Constructor.

    Args:
       report_type: rdf_stats.ClientGraphSeries.ReportType for the client stats
         to track.
    """
    self._report_type = report_type
    self.categories = dict([(x, {}) for x in self.active_days])

  def Add(self, category, label, age):
    """Adds another instance of this category into the active_days counter.

    We automatically count the event towards all relevant active_days. For
    example, if the category "Windows" was seen 8 days ago it will be counted
    towards the 30 day active, 14 day active but not against the 7 and 1 day
    actives.

    Args:
      category: The category name to account this instance against.
      label: Client label to which this should be applied.
      age: When this instance occurred.
    """
    now = rdfvalue.RDFDatetime.Now()
    category = utils.SmartUnicode(category)

    for active_time in self.active_days:
      self.categories[active_time].setdefault(label, {})
      if (now - age).ToFractional(
          rdfvalue.SECONDS) < active_time * 24 * 60 * 60:
        self.categories[active_time][label][
            category] = self.categories[active_time][label].get(category, 0) + 1

  def Save(self):
    """Generate a histogram object and store in the specified attribute."""
    graph_series_by_label = {}
    for active_time in self.active_days:
      for label in self.categories[active_time]:
        graphs_for_label = graph_series_by_label.setdefault(
            label, rdf_stats.ClientGraphSeries(report_type=self._report_type))
        graph = rdf_stats.Graph(title="%s day actives for %s label" %
                                (active_time, label))
        for k, v in sorted(self.categories[active_time][label].items()):
          graph.Append(label=k, y_value=v)
        graphs_for_label.graphs.Append(graph)

    for label, graph_series in graph_series_by_label.items():
      client_report_utils.WriteGraphSeries(graph_series, label)


_CLIENT_READ_BATCH_SIZE = 50000


def _IterateAllClients(recency_window=None):
  """Fetches client data from the relational db.

  Args:
    recency_window: An rdfvalue.Duration specifying a window of last-ping
      timestamps to consider. Clients that haven't communicated with GRR servers
      longer than the given period will be skipped. If recency_window is None,
      all clients will be iterated.

  Returns:
    Generator, yielding ClientFullInfo objects.
  """
  if recency_window is None:
    min_last_ping = None
  else:
    min_last_ping = rdfvalue.RDFDatetime.Now() - recency_window

  return data_store.REL_DB.IterateAllClientsFullInfo(min_last_ping,
                                                     _CLIENT_READ_BATCH_SIZE)


class InterrogationHuntMixin(object):
  """Mixin that provides logic to start interrogation hunts."""

  def GetOutputPlugins(self):
    """Returns list of OutputPluginDescriptor objects to be used in the hunt.

    This method can be overridden in a subclass in the server/local directory to
    apply plugins specific to the local installation.

    Returns:
      list of rdf_output_plugin.OutputPluginDescriptor objects
    """
    return []

  def StartInterrogationHunt(self):
    """Starts an interrogation hunt on all available clients."""
    flow_name = compatibility.GetName(flows_discovery.Interrogate)
    flow_args = flows_discovery.InterrogateArgs(lightweight=False)
    description = "Interrogate run by cron to keep host info fresh."

    hunt_id = hunt.CreateAndStartHunt(
        flow_name,
        flow_args,
        self.token.username,
        client_limit=0,
        client_rate=50,
        crash_limit=config.CONFIG["Cron.interrogate_crash_limit"],
        description=description,
        duration=rdfvalue.Duration.From(1, rdfvalue.WEEKS),
        output_plugins=self.GetOutputPlugins())
    self.Log("Started hunt %s.", hunt_id)


class InterrogateClientsCronJob(cronjobs.SystemCronJobBase,
                                InterrogationHuntMixin):
  """A cron job which runs an interrogate hunt on all clients.

  Interrogate needs to be run regularly on our clients to keep host information
  fresh and enable searching by username etc. in the GUI.
  """

  frequency = rdfvalue.Duration.From(1, rdfvalue.WEEKS)
  # This just starts a hunt, which should be essentially instantantaneous
  lifetime = rdfvalue.Duration.From(30, rdfvalue.MINUTES)

  def Run(self):
    self.StartInterrogationHunt()


class PurgeClientStatsCronJob(cronjobs.SystemCronJobBase):
  """Deletes outdated client statistics."""

  frequency = rdfvalue.Duration.From(1, rdfvalue.DAYS)
  lifetime = rdfvalue.Duration.From(20, rdfvalue.HOURS)

  def Run(self):
    end = rdfvalue.RDFDatetime.Now() - db.CLIENT_STATS_RETENTION

    total_deleted_count = 0
    for deleted_count in data_store.REL_DB.DeleteOldClientStats(
        yield_after_count=_STATS_DELETION_BATCH_SIZE, retention_time=end):
      self.HeartBeat()
      total_deleted_count += deleted_count
      self.Log("Deleted %d ClientStats that expired before %s",
               total_deleted_count, end)
