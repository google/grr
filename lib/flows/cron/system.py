#!/usr/bin/env python
"""These flows are system-specific GRR cron flows."""


import bisect
import time

import logging

from grr.endtoend_tests import base
from grr.lib import access_control
from grr.lib import aff4
from grr.lib import config_lib
from grr.lib import data_store
from grr.lib import export_utils
from grr.lib import flow
from grr.lib import hunts
from grr.lib import rdfvalue
from grr.lib import utils
from grr.lib.aff4_objects import cronjobs
from grr.lib.rdfvalues import stats


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
      if (now - age).seconds < active_time * 24 * 60 * 60:
        self.categories[active_time][category] = self.categories[
            active_time].get(category, 0) + 1

  def Save(self, fd):
    """Generate a histogram object and store in the specified attribute."""
    histogram = self.attribute()
    for active_time in self.active_days:
      graph = stats.Graph(title="%s day actives" % active_time)
      for k, v in sorted(self.categories[active_time].items()):
        graph.Append(label=k, y_value=v)

      histogram.Append(graph)

    # Add an additional instance of this histogram (without removing previous
    # instances).
    fd.AddAttribute(histogram)


class AbstractClientStatsCronFlow(cronjobs.SystemCronFlow):
  """A cron job which opens every client in the system.

  We feed all the client objects to the AbstractClientStatsCollector instances.
  """

  CLIENT_STATS_URN = rdfvalue.RDFURN("aff4:/stats/ClientFleetStats")

  def BeginProcessing(self):
    pass

  def ProcessClient(self, client):
    raise NotImplementedError()

  def FinishProcessing(self):
    pass

  @flow.StateHandler()
  def Start(self):
    """Retrieve all the clients for the AbstractClientStatsCollectors."""
    try:
      self.stats = aff4.FACTORY.Create(self.CLIENT_STATS_URN,
                                       "ClientFleetStats",
                                       mode="w", token=self.token)
      self.BeginProcessing()

      root = aff4.FACTORY.Open(aff4.ROOT_URN, token=self.token)
      children_urns = list(root.ListChildren())
      logging.debug("Found %d children.", len(children_urns))

      processed_count = 0
      for child in aff4.FACTORY.MultiOpen(
          children_urns, mode="r", token=self.token, age=aff4.NEWEST_TIME):
        if isinstance(child, aff4.AFF4Object.VFSGRRClient):
          self.ProcessClient(child)
          processed_count += 1

        # This flow is not dead: we don't want to run out of lease time.
        self.HeartBeat()

      self.FinishProcessing()
      self.stats.Close()

      logging.info("%s: processed %d clients.", self.__class__.__name__,
                   processed_count)
    except Exception as e:  # pylint: disable=broad-except
      logging.exception("Error while calculating stats: %s", e)
      raise


class GRRVersionBreakDown(AbstractClientStatsCronFlow):
  """Records relative ratios of GRR versions in 7 day actives."""

  frequency = rdfvalue.Duration("4h")

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

    uname = client.Get(client.Schema.UNAME, "Unknown")
    # Windows-2008ServerR2-6.1.7601SP1, Linux-Ubuntu-12.04,
    # Darwin-OSX-10.9.3
    self.counters[1].Add(uname, ping)


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
      pos = bisect.bisect(self._bins, time_ago.microseconds)

      # If clients are older than the last bin forget them.
      try:
        self._value[pos] += 1
      except IndexError:
        pass


class InterrogateClientsCronFlow(cronjobs.SystemCronFlow):
  """A cron job which runs an interrogate hunt on all clients.

  Interrogate needs to be run regularly on our clients to keep host information
  fresh and enable searching by username etc. in the GUI.
  """
  frequency = rdfvalue.Duration("1w")
  # This just starts a hunt, which should be essentially instantantaneous
  lifetime = rdfvalue.Duration("30m")

  def GetOutputPlugins(self):
    """Returns list of rdfvalue.OutputPlugin objects to be used in the hunt.

    This method can be overridden in a subclass in the server/local directory to
    apply plugins specific to the local installation.

    Returns:
      list of rdfvalue.OutputPlugin objects
    """
    return []

  @flow.StateHandler()
  def Start(self):
    with hunts.GRRHunt.StartHunt(
        hunt_name="GenericHunt",
        flow_runner_args=rdfvalue.FlowRunnerArgs(flow_name="Interrogate"),
        flow_args=rdfvalue.InterrogateArgs(lightweight=False),
        regex_rules=[],
        output_plugins=self.GetOutputPlugins(),
        token=self.token) as hunt:

      runner = hunt.GetRunner()
      runner.args.client_rate = 50
      runner.args.expiry_time = "1w"
      runner.args.description = ("Interrogate run by cron to keep host"
                                 "info fresh.")
      runner.Start()


class StatsHuntCronFlow(cronjobs.SystemCronFlow):
  """A cron job which runs a continuous stats hunt on all clients.

  This hunt is designed to collect lightweight information from all clients with
  very high resolution (similar to poll period). We roll over to a new hunt to
  move to a new collection, and pick up any clients that might have fallen out
  of the collection loop due to a worker dying or some other problem.
  """
  frequency = rdfvalue.Duration("1d")
  # This just starts a hunt, which should be essentially instantantaneous
  lifetime = rdfvalue.Duration("30m")

  def GetOutputPlugins(self):
    """Returns list of rdfvalue.OutputPlugin objects to be used in the hunt.

    This method can be overridden in a subclass in the server/local directory to
    apply plugins specific to the local installation.

    Returns:
      list of rdfvalue.OutputPlugin objects
    """
    return []

  @flow.StateHandler()
  def Start(self):
    with hunts.GRRHunt.StartHunt(
        hunt_name="StatsHunt",
        output_plugins=self.GetOutputPlugins(),
        regex_rules=[],
        token=self.token) as hunt:

      runner = hunt.GetRunner()
      runner.args.client_rate = 0
      runner.args.client_limit = config_lib.CONFIG.Get("StatsHunt.ClientLimit")
      runner.args.expiry_time = self.frequency
      runner.args.description = "Stats hunt for high-res client info."
      runner.Start()


class PurgeClientStats(cronjobs.SystemCronFlow):
  """Deletes outdated client statistics."""

  frequency = rdfvalue.Duration("1w")

  # Keep stats for one month.
  MAX_AGE = 31 * 24 * 3600

  @flow.StateHandler(next_state="ProcessClients")
  def Start(self):
    """Calls "Process" state to avoid spending too much time in Start."""
    self.CallState(next_state="ProcessClients")

  @flow.StateHandler()
  def ProcessClients(self, unused_responses):
    """Does the work."""
    self.start = 0
    self.end = int(1e6 * (time.time() - self.MAX_AGE))

    client_urns = export_utils.GetAllClients(token=self.token)

    for client_urn in client_urns:
      data_store.DB.DeleteAttributes(client_urn.Add("stats"),
                                     [u"aff4:stats"],
                                     start=self.start, end=self.end, sync=False,
                                     token=self.token)
      self.HeartBeat()

    data_store.DB.Flush()


class EndToEndTests(cronjobs.SystemCronFlow):
  """Runs end-to-end tests on designated clients.

  Raise if any there are any test failures on any clients.  We want to be able
  to alert on these failures.
  """
  frequency = rdfvalue.Duration("1d")
  lifetime = rdfvalue.Duration("2h")

  def GetOutputPlugins(self):
    """Returns list of rdfvalue.OutputPlugin objects to be used in the hunt."""
    return []

  @flow.StateHandler(next_state="CheckResults")
  def Start(self):
    self.state.Register("hunt_id", None)
    self.state.Register("client_ids", set())
    self.state.Register("client_ids_failures", set())
    self.state.Register("client_ids_result_reported", set())

    self.state.client_ids = base.GetClientTestTargets(token=self.token)

    if not self.state.client_ids:
      self.Log("No clients to test on, define them in "
               "Test.end_to_end_client_ids")
      return

    token = access_control.ACLToken(username="GRRWorker",
                                    reason="Running endtoend tests.").SetUID()
    runner_args = rdfvalue.FlowRunnerArgs(flow_name="EndToEndTestFlow")

    flow_request = rdfvalue.FlowRequest(
        client_ids=self.state.client_ids,
        args=rdfvalue.EndToEndTestFlowArgs(),
        runner_args=runner_args)

    bogus_rule = rdfvalue.ForemanAttributeRegex(
        attribute_name="System", attribute_regex="Does not match anything")

    hunt_args = rdfvalue.VariableGenericHuntArgs(flows=[flow_request])

    hunt_args.output_plugins = self.GetOutputPlugins()

    with hunts.GRRHunt.StartHunt(
        hunt_name="VariableGenericHunt",
        args=hunt_args,
        regex_rules=[bogus_rule],
        client_rate=0,
        expiry_time="1d",
        token=token) as hunt:

      self.state.hunt_id = hunt.session_id
      hunt.SetDescription("EndToEnd tests run by cron")
      hunt.Run()
      hunt.ManuallyScheduleClients(token=token)

    # Set a callback to check the results after 50 minutes.  This should be
    # plenty of time for the clients to receive the hunt and run the tests, but
    # not so long that the flow lease will expire.

    wait_duration = rdfvalue.Duration(
        config_lib.CONFIG.Get("Test.end_to_end_result_check_wait"))
    completed_time = rdfvalue.RDFDatetime().Now() + wait_duration

    self.CallState(next_state="CheckResults", start_time=completed_time)

  def _CheckForFailures(self, result):
    self.state.client_ids_result_reported.add(result.source)
    if not result.payload.success:
      self.state.client_ids_failures.add(result.source)

  def _CheckForSuccess(self, results):
    """Check the hunt results to see if it succeeded overall.

    Args:
      results: results collection open for reading
    Raises:
      flow.FlowError: if incomplete results, or test failures.
    """
    # Check the actual test results
    map(self._CheckForFailures, results)

    # Check that all the clients that got the flow reported some results
    self.state.client_ids_failures.update(self.state.client_ids -
                                          self.state.client_ids_result_reported)

    if self.state.client_ids_failures:
      raise flow.FlowError("Tests failed on clients: %s. Check hunt %s for "
                           "errors." % (self.state.client_ids_failures,
                                        self.state.hunt_id))

  @flow.StateHandler()
  def CheckResults(self):
    """Check tests passed.

    The EndToEndTestFlow will report all test results, we just need to look for
    any failures.
    """
    with aff4.FACTORY.Open(
        self.state.hunt_id.Add("Results"), token=self.token) as results:
      self._CheckForSuccess(results)
      self.Log("Tests passed on all clients: %s", self.state.client_ids)
