#!/usr/bin/env python
"""These flows are system-specific GRR cron flows."""


import bisect
import time

from grr.lib import aff4
from grr.lib import data_store
from grr.lib import export_utils
from grr.lib import flow
from grr.lib import rdfvalue

from grr.lib import utils
from grr.proto import analysis_pb2


class SystemCronFlow(flow.GRRFlow):
  frequency = rdfvalue.Duration("1d")

  __abstract = True  # pylint: disable=g-bad-name


class Sample(rdfvalue.RDFProtoStruct):
  """A Graph sample is a single data point."""
  protobuf = analysis_pb2.Sample


class Graph(rdfvalue.RDFProtoStruct):
  """A Graph is a collection of sample points."""
  protobuf = analysis_pb2.Graph

  def Append(self, **kwargs):
    self.data.Append(**kwargs)

  def __len__(self):
    return len(self.data)

  def __getitem__(self, item):
    return Sample(self.data[item])

  def __iter__(self):
    for x in self.data:
      yield Sample(x)


class GraphSeries(rdfvalue.RDFValueArray):
  """A sequence of graphs (e.g. evolving over time)."""
  rdf_type = Graph


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

  def Add(self, category, age):
    """Adds another instance of this category into the active_days counter.

    We automatically count the event towards all relevant active_days. For
    example, if the category "Windows" was seen 8 days ago it will be counted
    towards the 30 day active, 14 day active but not against the 7 and 1 day
    actives.

    Args:
      category: The category name to account this instance against.
      age: When this instance occurred.
    """
    now = rdfvalue.RDFDatetime().Now()
    category = utils.SmartUnicode(category)

    for active_time in self.active_days:
      if now - age < active_time * 24 * 60 * 60 * 1e6:
        self.categories[active_time][category] = self.categories[
            active_time].get(category, 0) + 1

  def Save(self, fd):
    """Generate a histogram object and store in the specified attribute."""
    histogram = self.attribute()
    for active_time in self.active_days:
      graph = Graph(title="%s day actives" % active_time)
      for k, v in sorted(self.categories[active_time].items()):
        graph.Append(label=k, y_value=v)

      histogram.Append(graph)

    # Add an additional instance of this histogram (without removing previous
    # instances).
    fd.AddAttribute(histogram)


class ClientFleetStats(aff4.AFF4Object):
  """AFF4 object for storing client statistics."""

  class SchemaCls(aff4.AFF4Object.SchemaCls):
    """Schema for ClientFleetStats object."""

    GRRVERSION_HISTOGRAM = aff4.Attribute("aff4:stats/grrversion", GraphSeries,
                                          "GRR version statistics for active "
                                          "clients.")

    OS_HISTOGRAM = aff4.Attribute(
        "aff4:stats/os_type", GraphSeries,
        "Operating System statistics for active clients.")

    RELEASE_HISTOGRAM = aff4.Attribute("aff4:stats/release", GraphSeries,
                                       "Release statistics for active clients.")

    VERSION_HISTOGRAM = aff4.Attribute("aff4:stats/version", GraphSeries,
                                       "Version statistics for active clients.")

    LAST_CONTACTED_HISTOGRAM = aff4.Attribute("aff4:stats/last_contacted",
                                              Graph, "Last contacted time")


class AbstractClientStatsCronFlow(SystemCronFlow):
  """A cron job which opens every client in the system.

  We feed all the client objects to the AbstractClientStatsCollector instances.
  """

  CLIENT_STATS_URN = rdfvalue.RDFURN("aff4:/stats/ClientFleetStats")
  OPEN_CHUNK_LIMIT = 10000

  def BeginProcessing(self):
    pass

  def ProcessClient(self, client):
    raise NotImplementedError()

  def FinishProcessing(self):
    pass

  @flow.StateHandler(next_state="ProcessAllClients")
  def Start(self):
    """Calls "Process" state to avoid spending too much time in Start method."""
    self.CallState(next_state="ProcessAllClients")

  @flow.StateHandler()
  def ProcessAllClients(self, unused_responses):
    """Retrieve all the clients for the AbstractClientStatsCollectors."""
    self.stats = aff4.FACTORY.Create(self.CLIENT_STATS_URN, "ClientFleetStats",
                                     mode="w", token=self.token)
    self.BeginProcessing()
    try:
      root = aff4.FACTORY.Open(aff4.ROOT_URN, token=self.token)
      children_urns = list(root.ListChildren())

      while children_urns:
        to_read = children_urns[:self.OPEN_CHUNK_LIMIT]
        children_urns = children_urns[self.OPEN_CHUNK_LIMIT:]
        for child in aff4.FACTORY.MultiOpen(to_read, mode="r", token=self.token,
                                            age=aff4.NEWEST_TIME):
          self.ProcessClient(child)

        # This flow is not dead: we don't want to run out of lease time.
        self.Ping()
    finally:
      self.FinishProcessing()
      self.stats.Close()


class GRRVersionBreakDown(AbstractClientStatsCronFlow):
  """Records relative ratios of GRR versions in 7 day actives."""

  frequency = "4h"

  def BeginProcessing(self):
    self.counter = _ActiveCounter(self.stats.Schema.GRRVERSION_HISTOGRAM)

  def FinishProcessing(self):
    self.counter.Save(self.stats)

  def ProcessClient(self, client):
    ping = client.Get(client.Schema.PING)
    c_info = client.Get(client.Schema.CLIENT_INFO)
    if c_info and ping:
      category = " ".join([c_info.client_description or c_info.client_name,
                           str(c_info.client_version)])

      self.counter.Add(category, ping)


class OSBreakDown(AbstractClientStatsCronFlow):
  """Records relative ratios of OS versions in 7 day actives."""

  def BeginProcessing(self):
    self.counters = [
        _ActiveCounter(self.stats.Schema.OS_HISTOGRAM),
        _ActiveCounter(self.stats.Schema.VERSION_HISTOGRAM),
        _ActiveCounter(self.stats.Schema.RELEASE_HISTOGRAM),
        ]

  def FinishProcessing(self):
    # Write all the counter attributes.
    for counter in self.counters:
      counter.Save(self.stats)

  def ProcessClient(self, client):
    """Update counters for system, version and release attributes."""
    ping = client.Get(client.Schema.PING)
    if not ping:
      return
    system = client.Get(client.Schema.SYSTEM, "Unknown")
    # Windows, Linux, Darwin
    self.counters[0].Add(system, ping)

    version = client.Get(client.Schema.VERSION, "Unknown")
    # Windows XP, Linux Ubuntu, Darwin OSX
    self.counters[1].Add("%s %s" % (system, version), ping)

    release = client.Get(client.Schema.OS_RELEASE, "Unknown")
    # Windows XP 5.1.2600 SP3, Linux Ubuntu 12.04, Darwin OSX 10.8.2
    self.counters[2].Add("%s %s %s" % (system, version, release), ping)


class LastAccessStats(AbstractClientStatsCronFlow):
  """Calculates a histogram statistics of clients last contacted times."""

  # The number of clients fall into these bins (number of hours ago)
  _bins = [1, 2, 3, 7, 14, 30, 60]

  def BeginProcessing(self):
    self._bins = [long(x*1e6*24*60*60) for x in self._bins]

    # We will count them in this bin
    self._value = [0] * len(self._bins)

  def FinishProcessing(self):
    # Build and store the graph now. Day actives are cumulative.
    cumulative_count = 0
    graph = self.stats.Schema.LAST_CONTACTED_HISTOGRAM()
    for x, y in zip(self._bins, self._value):
      cumulative_count += y
      graph.Append(x_value=x, y_value=cumulative_count)

    self.stats.AddAttribute(graph)

  def ProcessClient(self, client):
    now = rdfvalue.RDFDatetime().Now()

    ping = client.Get(client.Schema.PING)
    if ping:
      time_ago = now - ping
      pos = bisect.bisect(self._bins, time_ago)

      # If clients are older than the last bin forget them.
      try:
        self._value[pos] += 1
      except IndexError:
        pass


