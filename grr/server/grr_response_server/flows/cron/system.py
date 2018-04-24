#!/usr/bin/env python
"""These flows are system-specific GRR cron flows."""

import bisect
import logging
import time

from grr.lib import rdfvalue
from grr.lib import utils
from grr.lib.rdfvalues import flows as rdf_flows
from grr.lib.rdfvalues import stats as rdf_stats
from grr.server.grr_response_server import aff4
from grr.server.grr_response_server import data_store
from grr.server.grr_response_server import export_utils
from grr.server.grr_response_server import flow
from grr.server.grr_response_server.aff4_objects import aff4_grr
from grr.server.grr_response_server.aff4_objects import cronjobs
from grr.server.grr_response_server.aff4_objects import stats as aff4_stats
from grr.server.grr_response_server.flows.general import discovery as flows_discovery
from grr.server.grr_response_server.hunts import implementation as hunts_implementation
from grr.server.grr_response_server.hunts import standard as hunts_standard


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
      for label in self.categories[active_time].keys():
        histograms.setdefault(label, self.attribute())
        graph = rdf_stats.Graph(title="%s day actives for %s label" % (
            active_time, label))
        for k, v in sorted(self.categories[active_time][label].items()):
          graph.Append(label=k, y_value=v)

        histograms[label].Append(graph)

    for label, histogram in histograms.items():
      # Add an additional instance of this histogram (without removing previous
      # instances).
      # pylint: disable=protected-access
      cron_flow._StatsForLabel(label).AddAttribute(histogram)
      # pylint: enable=protected-access


class AbstractClientStatsCronFlow(cronjobs.SystemCronFlow):
  """A cron job which opens every client in the system.

  We feed all the client objects to the AbstractClientStatsCollector instances.
  """

  CLIENT_STATS_URN = rdfvalue.RDFURN("aff4:/stats/ClientFleetStats")

  def BeginProcessing(self):
    pass

  def ProcessLegacyClient(self, client):
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

  def _IterateLegacyClients(self):
    root = aff4.FACTORY.Open(aff4.ROOT_URN, token=self.token)
    children_urns = list(root.ListChildren())
    logging.debug("Found %d children.", len(children_urns))

    for child in aff4.FACTORY.MultiOpen(
        children_urns, mode="r", token=self.token, age=aff4.NEWEST_TIME):
      if isinstance(child, aff4_grr.VFSGRRClient):
        yield child

  def _IterateClients(self):
    for c in data_store.REL_DB.IterateAllClientsFullInfo():
      yield c

  @flow.StateHandler()
  def Start(self):
    """Retrieve all the clients for the AbstractClientStatsCollectors."""
    try:

      self.stats = {}

      self.BeginProcessing()

      if data_store.RelationalDBReadEnabled():
        clients = self._IterateClients()
      else:
        clients = self._IterateLegacyClients()

      processed_count = 0
      for c in clients:
        if data_store.RelationalDBReadEnabled():
          self.ProcessClientFullInfo(c)
        else:
          self.ProcessLegacyClient(c)
        processed_count += 1

        # This flow is not dead: we don't want to run out of lease time.
        self.HeartBeat()

      self.FinishProcessing()
      for fd in self.stats.values():
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

  def ProcessLegacyClient(self, client):
    ping = client.Get(client.Schema.PING)
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

  def ProcessLegacyClient(self, client):
    """Update counters for system, version and release attributes."""
    labels = self._GetClientLabelsList(client)
    ping = client.Get(client.Schema.PING)
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
    self._bins = [long(x * 1e6 * 24 * 60 * 60) for x in self._bins]

    self.values = {}

  def FinishProcessing(self):
    # Build and store the graph now. Day actives are cumulative.
    for label in self.values.iterkeys():
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

  def ProcessLegacyClient(self, client):
    labels = self._GetClientLabelsList(client)
    ping = client.Get(client.Schema.PING)

    self._Process(labels, ping)

  def ProcessClientFullInfo(self, client_full_info):
    labels = self._GetClientLabelsList(client_full_info)
    ping = client_full_info.metadata.ping

    self._Process(labels, ping)


class InterrogateClientsCronFlow(cronjobs.SystemCronFlow):
  """A cron job which runs an interrogate hunt on all clients.

  Interrogate needs to be run regularly on our clients to keep host information
  fresh and enable searching by username etc. in the GUI.
  """
  frequency = rdfvalue.Duration("1w")
  # This just starts a hunt, which should be essentially instantantaneous
  lifetime = rdfvalue.Duration("30m")

  def GetOutputPlugins(self):
    """Returns list of OutputPluginDescriptor objects to be used in the hunt.

    This method can be overridden in a subclass in the server/local directory to
    apply plugins specific to the local installation.

    Returns:
      list of output_plugin.OutputPluginDescriptor objects
    """
    return []

  @flow.StateHandler()
  def Start(self):
    with hunts_implementation.GRRHunt.StartHunt(
        hunt_name=hunts_standard.GenericHunt.__name__,
        client_limit=0,
        flow_runner_args=rdf_flows.FlowRunnerArgs(
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


class PurgeClientStats(cronjobs.SystemCronFlow):
  """Deletes outdated client statistics."""

  frequency = rdfvalue.Duration("1w")

  # Keep stats for one month.
  MAX_AGE = 31 * 24 * 3600

  @flow.StateHandler()
  def Start(self):
    """Calls "Process" state to avoid spending too much time in Start."""
    self.CallState(next_state="ProcessClients")

  @flow.StateHandler()
  def ProcessClients(self, unused_responses):
    """Does the work."""
    self.start = 0
    self.end = int(1e6 * (time.time() - self.MAX_AGE))

    client_urns = export_utils.GetAllClients(token=self.token)

    for batch in utils.Grouper(client_urns, 10000):
      with data_store.DB.GetMutationPool() as mutation_pool:
        for client_urn in batch:
          mutation_pool.DeleteAttributes(
              client_urn.Add("stats"), [u"aff4:stats"],
              start=self.start,
              end=self.end)
      self.HeartBeat()
