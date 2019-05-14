#!/usr/bin/env python
"""These flows are system-specific GRR cron flows."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import bisect
import logging


from future.builtins import zip
from future.utils import iteritems
from future.utils import itervalues

from grr_response_core import config
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import stats as rdf_stats
from grr_response_core.lib.util import collection
from grr_response_core.lib.util import compatibility
from grr_response_server import aff4
from grr_response_server import client_report_utils
from grr_response_server import cronjobs
from grr_response_server import data_store
from grr_response_server import export_utils
from grr_response_server import hunt
from grr_response_server.aff4_objects import aff4_grr
from grr_response_server.aff4_objects import cronjobs as aff4_cronjobs
from grr_response_server.aff4_objects import stats as aff4_stats
from grr_response_server.databases import db
from grr_response_server.flows.general import discovery as flows_discovery
from grr_response_server.hunts import implementation as hunts_implementation
from grr_response_server.hunts import standard as hunts_standard
from grr_response_server.rdfvalues import flow_runner as rdf_flow_runner

# Maximum number of old stats entries to delete in a single db call.
_STATS_DELETION_BATCH_SIZE = 10000

# How often to save progress to the DB when deleting stats.
_stats_checkpoint_period = rdfvalue.Duration("15m")


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
      if (now - age).seconds < active_time * 24 * 60 * 60:
        self.categories[active_time][label][
            category] = self.categories[active_time][label].get(category, 0) + 1

  def Save(self, token=None):
    """Generate a histogram object and store in the specified attribute."""
    graph_series_by_label = {}
    for active_time in self.active_days:
      for label in self.categories[active_time]:
        graphs_for_label = graph_series_by_label.setdefault(
            label, rdf_stats.ClientGraphSeries(report_type=self._report_type))
        graph = rdf_stats.Graph(title="%s day actives for %s label" %
                                (active_time, label))
        for k, v in sorted(iteritems(self.categories[active_time][label])):
          graph.Append(label=k, y_value=v)
        graphs_for_label.graphs.Append(graph)

    for label, graph_series in iteritems(graph_series_by_label):
      client_report_utils.WriteGraphSeries(graph_series, label, token=token)


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


class AbstractClientStatsCronJob(cronjobs.SystemCronJobBase):
  """Base class for all stats processing cron jobs."""

  CLIENT_STATS_URN = rdfvalue.RDFURN("aff4:/stats/ClientFleetStats")

  # An rdfvalue.Duration specifying a window of last-ping
  # timestamps to analyze. Clients that haven't communicated with GRR servers
  # longer than the given period will be skipped.
  recency_window = None

  def BeginProcessing(self):
    pass

  def ProcessClientFullInfo(self, client_full_info):
    raise NotImplementedError()

  def FinishProcessing(self):
    pass

  def _GetClientLabelsList(self, client):
    """Get set of labels applied to this client."""
    return set(["All"] + list(client.GetLabelsNames(owner="GRR")))

  def _StatsForLabel(self, label):
    if label not in self.stats:
      self.stats[label] = aff4.FACTORY.Create(
          self.CLIENT_STATS_URN.Add(label),
          aff4_stats.ClientFleetStats,
          mode="w",
          token=self.token)
    return self.stats[label]

  def Run(self):
    """Retrieve all the clients for the AbstractClientStatsCollectors."""
    try:

      self.stats = {}

      self.BeginProcessing()

      processed_count = 0

      for client_info in _IterateAllClients(recency_window=self.recency_window):
        self.ProcessClientFullInfo(client_info)
        processed_count += 1

        if processed_count % _CLIENT_READ_BATCH_SIZE == 0:
          self.Log("Processed %d clients.", processed_count)
          self.HeartBeat()

      if processed_count != 0:
        self.Log("Processed %d clients.", processed_count)

      self.FinishProcessing()
      for fd in itervalues(self.stats):
        fd.Close()

      logging.info("%s: processed %d clients.", self.__class__.__name__,
                   processed_count)
    except Exception as e:  # pylint: disable=broad-except
      logging.exception("Error while calculating stats: %s", e)
      raise


class GRRVersionBreakDownCronJob(AbstractClientStatsCronJob):
  """Records relative ratios of GRR versions in 7 day actives."""

  frequency = rdfvalue.Duration("6h")
  lifetime = rdfvalue.Duration("6h")
  recency_window = rdfvalue.Duration("30d")

  def BeginProcessing(self):
    self.counter = _ActiveCounter(
        rdf_stats.ClientGraphSeries.ReportType.GRR_VERSION)

  def FinishProcessing(self):
    self.counter.Save(token=self.token)

  def ProcessClientFullInfo(self, client_full_info):
    c_info = client_full_info.last_startup_info.client_info
    ping = client_full_info.metadata.ping
    labels = self._GetClientLabelsList(client_full_info)

    if not (c_info and ping):
      return

    category = " ".join([
        c_info.client_description or c_info.client_name,
        str(c_info.client_version)
    ])

    for label in labels:
      self.counter.Add(category, label, ping)


class OSBreakDownCronJob(AbstractClientStatsCronJob):
  """Records relative ratios of OS versions in 7 day actives."""

  frequency = rdfvalue.Duration("1d")
  lifetime = rdfvalue.Duration("20h")
  recency_window = rdfvalue.Duration("30d")

  def BeginProcessing(self):
    self.counters = [
        _ActiveCounter(rdf_stats.ClientGraphSeries.ReportType.OS_TYPE),
        _ActiveCounter(rdf_stats.ClientGraphSeries.ReportType.OS_RELEASE),
    ]

  def FinishProcessing(self):
    # Write all the counter attributes.
    for counter in self.counters:
      counter.Save(token=self.token)

  def ProcessClientFullInfo(self, client_full_info):
    labels = self._GetClientLabelsList(client_full_info)
    ping = client_full_info.metadata.ping
    system = client_full_info.last_snapshot.knowledge_base.os
    uname = client_full_info.last_snapshot.Uname()

    if not ping:
      return

    for label in labels:
      # Windows, Linux, Darwin
      self.counters[0].Add(system, label, ping)

      # Windows-2008ServerR2-6.1.7601SP1, Linux-Ubuntu-12.04,
      # Darwin-OSX-10.9.3
      self.counters[1].Add(uname, label, ping)


class LastAccessStatsCronJob(AbstractClientStatsCronJob):
  """Calculates a histogram statistics of clients last contacted times."""

  frequency = rdfvalue.Duration("1d")
  lifetime = rdfvalue.Duration("20h")
  recency_window = rdfvalue.Duration("60d")

  # The number of clients fall into these bins (number of days ago)
  _bins = [1, 2, 3, 7, 14, 30, 60]

  def _ValuesForLabel(self, label):
    if label not in self.values:
      self.values[label] = [0] * len(self._bins)
    return self.values[label]

  def BeginProcessing(self):
    self._bins = [long(x * 1e6 * 24 * 60 * 60) for x in self._bins]

    self.values = {}

  def FinishProcessing(self):
    # Build and store the graph now. Day actives are cumulative.
    for label in self.values:
      cumulative_count = 0
      graph_series = rdf_stats.ClientGraphSeries(
          report_type=rdf_stats.ClientGraphSeries.ReportType.N_DAY_ACTIVE)
      graph_series.graphs.Append(rdf_stats.Graph())
      for x, y in zip(self._bins, self.values[label]):
        cumulative_count += y
        graph_series.graphs[0].Append(x_value=x, y_value=cumulative_count)
      client_report_utils.WriteGraphSeries(
          graph_series, label, token=self.token)

  def ProcessClientFullInfo(self, client_full_info):
    labels = self._GetClientLabelsList(client_full_info)
    ping = client_full_info.metadata.ping

    if not ping:
      return

    now = rdfvalue.RDFDatetime.Now()
    for label in labels:
      time_ago = now - ping
      pos = bisect.bisect(self._bins, time_ago.microseconds)

      # If clients are older than the last bin forget them.
      try:
        self._ValuesForLabel(label)[pos] += 1
      except IndexError:
        pass


class AbstractClientStatsCronFlow(aff4_cronjobs.SystemCronFlow):
  """A cron job which opens every client in the system.

  We feed all the client objects to the AbstractClientStatsCollector instances.
  """

  CLIENT_STATS_URN = rdfvalue.RDFURN("aff4:/stats/ClientFleetStats")

  # An rdfvalue.Duration specifying a window of last-ping
  # timestamps to analyze. Clients that haven't communicated with GRR servers
  # longer than the given period will be skipped.
  recency_window = None

  def BeginProcessing(self):
    pass

  def ProcessLegacyClient(self, ping, client):
    raise NotImplementedError()

  def ProcessClientFullInfo(self, client_full_info):
    raise NotImplementedError()

  def FinishProcessing(self):
    pass

  def _GetClientLabelsList(self, client):
    """Get set of labels applied to this client."""
    return set(["All"] + list(client.GetLabelsNames(owner="GRR")))

  def _StatsForLabel(self, label):
    if label not in self.stats:
      self.stats[label] = aff4.FACTORY.Create(
          self.CLIENT_STATS_URN.Add(label),
          aff4_stats.ClientFleetStats,
          mode="w",
          token=self.token)
    return self.stats[label]

  def Start(self):
    """Retrieve all the clients for the AbstractClientStatsCollectors."""
    try:

      self.stats = {}

      self.BeginProcessing()

      processed_count = 0

      if data_store.RelationalDBEnabled():
        for client_info in _IterateAllClients(
            recency_window=self.recency_window):
          self.ProcessClientFullInfo(client_info)
          processed_count += 1

          if processed_count % _CLIENT_READ_BATCH_SIZE == 0:
            self.Log("Processed %d clients.", processed_count)
            self.HeartBeat()

        if processed_count != 0:
          self.Log("Processed %d clients.", processed_count)

      else:
        root_children = aff4.FACTORY.Open(
            aff4.ROOT_URN, token=self.token).OpenChildren(mode="r")
        for batch in collection.Batch(root_children, _CLIENT_READ_BATCH_SIZE):
          for child in batch:
            if not isinstance(child, aff4_grr.VFSGRRClient):
              continue

            last_ping = child.Get(child.Schema.PING)

            self.ProcessLegacyClient(last_ping, child)
            processed_count += 1
            # This flow is not dead: we don't want to run out of lease time.
            self.HeartBeat()

      self.FinishProcessing()
      for fd in itervalues(self.stats):
        fd.Close()

      logging.info("%s: processed %d clients.", self.__class__.__name__,
                   processed_count)
    except Exception as e:  # pylint: disable=broad-except
      logging.exception("Error while calculating stats: %s", e)
      raise


class GRRVersionBreakDown(AbstractClientStatsCronFlow):
  """Records relative ratios of GRR versions in 7 day actives."""

  frequency = rdfvalue.Duration("4h")
  recency_window = rdfvalue.Duration("30d")

  def BeginProcessing(self):
    self.counter = _ActiveCounter(
        rdf_stats.ClientGraphSeries.ReportType.GRR_VERSION)

  def FinishProcessing(self):
    self.counter.Save(token=self.token)

  def _Process(self, labels, c_info, ping):
    if not (c_info and ping):
      return

    category = " ".join([
        c_info.client_description or c_info.client_name,
        str(c_info.client_version)
    ])

    for label in labels:
      self.counter.Add(category, label, ping)

  def ProcessLegacyClient(self, ping, client):
    c_info = client.Get(client.Schema.CLIENT_INFO)
    labels = self._GetClientLabelsList(client)

    self._Process(labels, c_info, ping)

  def ProcessClientFullInfo(self, client_full_info):
    c_info = client_full_info.last_startup_info.client_info
    ping = client_full_info.metadata.ping
    labels = self._GetClientLabelsList(client_full_info)

    self._Process(labels, c_info, ping)


class OSBreakDown(AbstractClientStatsCronFlow):
  """Records relative ratios of OS versions in 7 day actives."""

  recency_window = rdfvalue.Duration("30d")

  def BeginProcessing(self):
    self.counters = [
        _ActiveCounter(rdf_stats.ClientGraphSeries.ReportType.OS_TYPE),
        _ActiveCounter(rdf_stats.ClientGraphSeries.ReportType.OS_RELEASE),
    ]

  def FinishProcessing(self):
    # Write all the counter attributes.
    for counter in self.counters:
      counter.Save(self.token)

  def _Process(self, labels, ping, system, uname):
    if not ping:
      return

    for label in labels:
      # Windows, Linux, Darwin
      self.counters[0].Add(system, label, ping)

      # Windows-2008ServerR2-6.1.7601SP1, Linux-Ubuntu-12.04,
      # Darwin-OSX-10.9.3
      self.counters[1].Add(uname, label, ping)

  def ProcessLegacyClient(self, ping, client):
    """Update counters for system, version and release attributes."""
    labels = self._GetClientLabelsList(client)
    system = client.Get(client.Schema.SYSTEM, "Unknown")
    uname = client.Get(client.Schema.UNAME, "Unknown")

    self._Process(labels, ping, system, uname)

  def ProcessClientFullInfo(self, client_full_info):
    labels = self._GetClientLabelsList(client_full_info)
    ping = client_full_info.metadata.ping
    system = client_full_info.last_snapshot.knowledge_base.os
    uname = client_full_info.last_snapshot.Uname()

    self._Process(labels, ping, system, uname)


class LastAccessStats(AbstractClientStatsCronFlow):
  """Calculates a histogram statistics of clients last contacted times."""

  recency_window = rdfvalue.Duration("60d")

  # The number of clients fall into these bins (number of hours ago)
  _bins = [1, 2, 3, 7, 14, 30, 60]

  def _ValuesForLabel(self, label):
    if label not in self.values:
      self.values[label] = [0] * len(self._bins)
    return self.values[label]

  def BeginProcessing(self):
    self._bins = [x * 1e6 * 24 * 60 * 60 for x in self._bins]

    self.values = {}

  def FinishProcessing(self):
    # Build and store the graph now. Day actives are cumulative.
    for label in self.values:
      cumulative_count = 0
      graph_series = rdf_stats.ClientGraphSeries(
          report_type=rdf_stats.ClientGraphSeries.ReportType.N_DAY_ACTIVE)
      graph_series.graphs.Append(rdf_stats.Graph())
      for x, y in zip(self._bins, self.values[label]):
        cumulative_count += y
        graph_series.graphs[0].Append(x_value=x, y_value=cumulative_count)
      client_report_utils.WriteGraphSeries(
          graph_series, label, token=self.token)

  def _Process(self, labels, ping):
    if not ping:
      return

    now = rdfvalue.RDFDatetime.Now()
    for label in labels:
      time_ago = now - ping
      pos = bisect.bisect(self._bins, time_ago.microseconds)

      # If clients are older than the last bin forget them.
      try:
        self._ValuesForLabel(label)[pos] += 1
      except IndexError:
        pass

  def ProcessLegacyClient(self, ping, client):
    labels = self._GetClientLabelsList(client)
    self._Process(labels, ping)

  def ProcessClientFullInfo(self, client_full_info):
    labels = self._GetClientLabelsList(client_full_info)
    ping = client_full_info.metadata.ping

    self._Process(labels, ping)


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

    if data_store.RelationalDBEnabled():
      hunt_id = hunt.CreateAndStartHunt(
          flow_name,
          flow_args,
          self.token.username,
          client_limit=0,
          client_rate=50,
          crash_limit=config.CONFIG["Cron.interrogate_crash_limit"],
          description=description,
          duration=rdfvalue.Duration("1w"),
          output_plugins=self.GetOutputPlugins())
      self.Log("Started hunt %s.", hunt_id)
    else:
      with hunts_implementation.StartHunt(
          hunt_name=hunts_standard.GenericHunt.__name__,
          client_limit=0,
          flow_runner_args=rdf_flow_runner.FlowRunnerArgs(flow_name=flow_name),
          flow_args=flow_args,
          output_plugins=self.GetOutputPlugins(),
          crash_limit=config.CONFIG["Cron.interrogate_crash_limit"],
          client_rate=50,
          expiry_time=rdfvalue.Duration("1w"),
          description=description,
          token=self.token) as hunt_obj:

        hunt_obj.GetRunner().Start()
        self.Log("Started hunt %s.", hunt_obj.urn)


class InterrogateClientsCronFlow(aff4_cronjobs.SystemCronFlow,
                                 InterrogationHuntMixin):
  """The legacy cron flow which runs an interrogate hunt on all clients."""

  frequency = rdfvalue.Duration("1w")
  # This just starts a hunt, which should be essentially instantantaneous
  lifetime = rdfvalue.Duration("30m")

  def Start(self):
    self.StartInterrogationHunt()


class InterrogateClientsCronJob(cronjobs.SystemCronJobBase,
                                InterrogationHuntMixin):
  """A cron job which runs an interrogate hunt on all clients.

  Interrogate needs to be run regularly on our clients to keep host information
  fresh and enable searching by username etc. in the GUI.
  """

  frequency = rdfvalue.Duration("1w")
  # This just starts a hunt, which should be essentially instantantaneous
  lifetime = rdfvalue.Duration("30m")

  def Run(self):
    self.StartInterrogationHunt()


class PurgeClientStats(aff4_cronjobs.SystemCronFlow):
  """Deletes outdated client statistics."""

  frequency = rdfvalue.Duration("1w")

  def Start(self):
    """Calls "Process" state to avoid spending too much time in Start."""
    self.CallState(next_state="ProcessClients")

  def ProcessClients(self, responses):
    """Does the work."""
    del responses

    end = rdfvalue.RDFDatetime.Now() - db.CLIENT_STATS_RETENTION
    client_urns = export_utils.GetAllClients(token=self.token)

    for batch in collection.Batch(client_urns, 10000):
      with data_store.DB.GetMutationPool() as mutation_pool:
        for client_urn in batch:
          mutation_pool.DeleteAttributes(
              client_urn.Add("stats"), [u"aff4:stats"],
              start=0,
              end=end.AsMicrosecondsSinceEpoch())
      self.HeartBeat()

    if data_store.RelationalDBEnabled():
      total_deleted_count = 0
      for deleted_count in data_store.REL_DB.DeleteOldClientStats(
          yield_after_count=_STATS_DELETION_BATCH_SIZE, retention_time=end):
        self.HeartBeat()
        total_deleted_count += deleted_count
      self.Log("Deleted %d ClientStats that expired before %s",
               total_deleted_count, end)


class PurgeClientStatsCronJob(cronjobs.SystemCronJobBase):
  """Deletes outdated client statistics."""

  frequency = rdfvalue.Duration("1w")
  lifetime = rdfvalue.Duration("20h")

  def Run(self):
    end = rdfvalue.RDFDatetime.Now() - db.CLIENT_STATS_RETENTION

    if data_store.AFF4Enabled():
      client_urns = export_utils.GetAllClients(token=self.token)
      for batch in collection.Batch(client_urns, 10000):
        with data_store.DB.GetMutationPool() as mutation_pool:
          for client_urn in batch:
            mutation_pool.DeleteAttributes(
                client_urn.Add("stats"), [u"aff4:stats"],
                start=0,
                end=end.AsMicrosecondsSinceEpoch())
        self.HeartBeat()

    if data_store.RelationalDBEnabled():
      total_deleted_count = 0
      for deleted_count in data_store.REL_DB.DeleteOldClientStats(
          yield_after_count=_STATS_DELETION_BATCH_SIZE, retention_time=end):
        self.HeartBeat()
        total_deleted_count += deleted_count
        self.Log("Deleted %d ClientStats that expired before %s",
                 total_deleted_count, end)
