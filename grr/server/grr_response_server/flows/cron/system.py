#!/usr/bin/env python
"""These flows are system-specific GRR cron flows."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import bisect
import logging
import time


from builtins import zip  # pylint: disable=redefined-builtin
from future.utils import iteritems
from future.utils import itervalues
from future.utils import viewkeys

from fleetspeak.src.server.proto.fleetspeak_server import admin_pb2
from grr_response_core import config
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import stats as rdf_stats
from grr_response_core.lib.util import collection
from grr_response_server import aff4
from grr_response_server import cronjobs
from grr_response_server import data_store
from grr_response_server import export_utils
from grr_response_server import fleetspeak_connector
from grr_response_server import fleetspeak_utils
from grr_response_server.aff4_objects import aff4_grr
from grr_response_server.aff4_objects import cronjobs as aff4_cronjobs
from grr_response_server.aff4_objects import stats as aff4_stats
from grr_response_server.flows.general import discovery as flows_discovery
from grr_response_server.hunts import implementation as hunts_implementation
from grr_response_server.hunts import standard as hunts_standard
from grr_response_server.rdfvalues import flow_runner as rdf_flow_runner

# Maximum number of old stats entries to delete in a single db call.
_STATS_DELETION_BATCH_SIZE = 10000


class _ActiveCounter(object):
  """Helper class to count the number of times a specific category occurred.

  This class maintains running counts of event occurrence at different
  times. For example, the number of times an OS was reported as a category of
  "Windows" in the last 1 day, 7 days etc (as a measure of 7 day active windows
  systems).
  """

  active_days = [1, 7, 14, 30]

  def __init__(self, attribute):
    """Constructor.

    Args:
       attribute: The histogram object will be stored in this attribute.
    """
    self.attribute = attribute
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

  def Save(self, cron_flow):
    """Generate a histogram object and store in the specified attribute."""
    histograms = {}
    for active_time in self.active_days:
      for label in self.categories[active_time]:
        histograms.setdefault(label, self.attribute())
        graph = rdf_stats.Graph(title="%s day actives for %s label" %
                                (active_time, label))
        for k, v in sorted(iteritems(self.categories[active_time][label])):
          graph.Append(label=k, y_value=v)

        histograms[label].Append(graph)

    for label, histogram in iteritems(histograms):
      # Add an additional instance of this histogram (without removing previous
      # instances).
      # pylint: disable=protected-access
      cron_flow._StatsForLabel(label).AddAttribute(histogram)
      # pylint: enable=protected-access


def _GetLastContactFromFleetspeak(client_ids):
  """Fetches last contact times for the given clients from Fleetspeak.

  Args:
    client_ids: Iterable containing GRR client ids.

  Returns:
    A dict mapping the given client ids to timestamps representing when
    Fleetspeak last contacted the clients.
  """
  if not fleetspeak_connector.CONN or not fleetspeak_connector.CONN.outgoing:
    logging.warning(
        "Tried to get last-contact timestamps for Fleetspeak clients "
        "without an active connection to Fleetspeak.")
    return {}
  fs_ids = [fleetspeak_utils.GRRIDToFleetspeakID(cid) for cid in client_ids]
  fs_result = fleetspeak_connector.CONN.outgoing.ListClients(
      admin_pb2.ListClientsRequest(client_ids=fs_ids))
  if len(client_ids) != len(fs_result.clients):
    logging.error("Expected %d results from Fleetspeak; got %d instead.",
                  len(client_ids), len(fs_result.clients))
  last_contact_times = {}
  for fs_client in fs_result.clients:
    grr_id = fleetspeak_utils.FleetspeakIDToGRRID(fs_client.client_id)
    last_contact_times[grr_id] = fleetspeak_utils.TSToRDFDatetime(
        fs_client.last_contact_time)
  return last_contact_times


CLIENT_READ_BATCH_SIZE = 50000


def _IterateAllClients():
  """Fetches client data from the relational db."""
  all_client_ids = data_store.REL_DB.ReadAllClientIDs()
  for batch in collection.Batch(all_client_ids, CLIENT_READ_BATCH_SIZE):
    client_map = data_store.REL_DB.MultiReadClientFullInfo(batch)
    fs_client_ids = [
        cid for (cid, client) in iteritems(client_map)
        if client.metadata.fleetspeak_enabled
    ]
    last_contact_times = _GetLastContactFromFleetspeak(fs_client_ids)
    for cid, last_contact in iteritems(last_contact_times):
      client_map[cid].metadata.ping = last_contact
    for client in itervalues(client_map):
      yield client


def _IterateAllLegacyClients(token):
  """Fetches client data from the legacy db."""
  root_children = aff4.FACTORY.Open(
      aff4.ROOT_URN, token=token).OpenChildren(mode="r")
  for batch in collection.Batch(root_children, CLIENT_READ_BATCH_SIZE):
    fs_client_map = {}
    non_fs_clients = []
    for child in batch:
      if not isinstance(child, aff4_grr.VFSGRRClient):
        continue
      if child.Get(child.Schema.FLEETSPEAK_ENABLED):
        fs_client_map[child.urn.Basename()] = child
      else:
        non_fs_clients.append(child)
    last_contact_times = _GetLastContactFromFleetspeak(viewkeys(fs_client_map))
    for client in non_fs_clients:
      yield client.Get(client.Schema.PING), client
    for cid, client in iteritems(fs_client_map):
      last_contact = last_contact_times.get(cid, client.Get(client.Schema.PING))
      yield last_contact, client


class AbstractClientStatsCronJob(cronjobs.SystemCronJobBase):
  """Base class for all stats processing cron jobs."""

  CLIENT_STATS_URN = rdfvalue.RDFURN("aff4:/stats/ClientFleetStats")

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
      for client in _IterateAllClients():
        self.ProcessClientFullInfo(client)
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


class GRRVersionBreakDownCronJob(AbstractClientStatsCronJob):
  """Records relative ratios of GRR versions in 7 day actives."""

  frequency = rdfvalue.Duration("4h")
  lifetime = rdfvalue.Duration("4h")

  def BeginProcessing(self):
    self.counter = _ActiveCounter(
        aff4_stats.ClientFleetStats.SchemaCls.GRRVERSION_HISTOGRAM)

  def FinishProcessing(self):
    self.counter.Save(self)

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

  def BeginProcessing(self):
    self.counters = [
        _ActiveCounter(aff4_stats.ClientFleetStats.SchemaCls.OS_HISTOGRAM),
        _ActiveCounter(aff4_stats.ClientFleetStats.SchemaCls.RELEASE_HISTOGRAM),
    ]

  def FinishProcessing(self):
    # Write all the counter attributes.
    for counter in self.counters:
      counter.Save(self)

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
      graph = aff4_stats.ClientFleetStats.SchemaCls.LAST_CONTACTED_HISTOGRAM()
      for x, y in zip(self._bins, self.values[label]):
        cumulative_count += y
        graph.Append(x_value=x, y_value=cumulative_count)

      self._StatsForLabel(label).AddAttribute(graph)

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
      if data_store.RelationalDBReadEnabled():
        for client in _IterateAllClients():
          self.ProcessClientFullInfo(client)
          processed_count += 1
          # This flow is not dead: we don't want to run out of lease time.
          self.HeartBeat()
      else:
        for ping, client in _IterateAllLegacyClients(self.token):
          self.ProcessLegacyClient(ping, client)
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

  def BeginProcessing(self):
    self.counter = _ActiveCounter(
        aff4_stats.ClientFleetStats.SchemaCls.GRRVERSION_HISTOGRAM)

  def FinishProcessing(self):
    self.counter.Save(self)

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

  def BeginProcessing(self):
    self.counters = [
        _ActiveCounter(aff4_stats.ClientFleetStats.SchemaCls.OS_HISTOGRAM),
        _ActiveCounter(aff4_stats.ClientFleetStats.SchemaCls.RELEASE_HISTOGRAM),
    ]

  def FinishProcessing(self):
    # Write all the counter attributes.
    for counter in self.counters:
      counter.Save(self)

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
      graph = aff4_stats.ClientFleetStats.SchemaCls.LAST_CONTACTED_HISTOGRAM()
      for x, y in zip(self._bins, self.values[label]):
        cumulative_count += y
        graph.Append(x_value=x, y_value=cumulative_count)

      self._StatsForLabel(label).AddAttribute(graph)

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
    with hunts_implementation.StartHunt(
        hunt_name=hunts_standard.GenericHunt.__name__,
        client_limit=0,
        flow_runner_args=rdf_flow_runner.FlowRunnerArgs(
            flow_name=flows_discovery.Interrogate.__name__),
        flow_args=flows_discovery.InterrogateArgs(lightweight=False),
        output_plugins=self.GetOutputPlugins(),
        token=self.token) as hunt:

      runner = hunt.GetRunner()
      runner.runner_args.crash_limit = 500
      runner.runner_args.client_rate = 50
      runner.runner_args.expiry_time = "1w"
      runner.runner_args.description = ("Interrogate run by cron to keep host"
                                        "info fresh.")
      runner.Start()


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

  # Keep stats for one month.
  MAX_AGE = 31 * 24 * 3600

  def Start(self):
    """Calls "Process" state to avoid spending too much time in Start."""
    self.CallState(next_state="ProcessClients")

  def ProcessClients(self, responses):
    """Does the work."""
    del responses
    self.start = 0
    self.end = int(1e6 * (time.time() - self.MAX_AGE))

    client_urns = export_utils.GetAllClients(token=self.token)

    for batch in collection.Batch(client_urns, 10000):
      with data_store.DB.GetMutationPool() as mutation_pool:
        for client_urn in batch:
          mutation_pool.DeleteAttributes(
              client_urn.Add("stats"), [u"aff4:stats"],
              start=self.start,
              end=self.end)
      self.HeartBeat()


class PurgeClientStatsCronJob(cronjobs.SystemCronJobBase):
  """Deletes outdated client statistics."""

  frequency = rdfvalue.Duration("1w")
  lifetime = rdfvalue.Duration("20h")

  # Keep stats for one month.
  MAX_AGE = 31 * 24 * 3600

  def Run(self):
    self.start = 0
    self.end = int(1e6 * (time.time() - self.MAX_AGE))

    client_urns = export_utils.GetAllClients(token=self.token)

    for batch in collection.Batch(client_urns, 10000):
      with data_store.DB.GetMutationPool() as mutation_pool:
        for client_urn in batch:
          mutation_pool.DeleteAttributes(
              client_urn.Add("stats"), [u"aff4:stats"],
              start=self.start,
              end=self.end)
      self.HeartBeat()


class PurgeServerStatsCronJob(cronjobs.SystemCronJobBase):
  """Cronjob that deletes old stats entries from the relational DB."""

  frequency = rdfvalue.Duration("3h")
  lifetime = rdfvalue.Duration("2h")

  def Run(self):
    # Old stats in the legacy datastore get deleted after every write.
    if not data_store.RelationalDBReadEnabled(category="stats"):
      return
    stats_ttl = (
        rdfvalue.Duration("1h") * config.CONFIG["StatsStore.stats_ttl_hours"])
    cutoff = rdfvalue.RDFDatetime.Now() - stats_ttl
    deletion_complete = False
    total_entries_deleted = 0
    while not deletion_complete:
      num_entries_deleted = data_store.REL_DB.DeleteStatsStoreEntriesOlderThan(
          cutoff, _STATS_DELETION_BATCH_SIZE)
      total_entries_deleted += num_entries_deleted
      if num_entries_deleted >= _STATS_DELETION_BATCH_SIZE:
        self.HeartBeat()
        continue

      total_entries_deleted += (
          data_store.REL_DB.DeleteStatsStoreEntriesOlderThan(
              cutoff, _STATS_DELETION_BATCH_SIZE))
      deletion_complete = True
    self.Log("Deleted %d stats entries.", total_entries_deleted)
