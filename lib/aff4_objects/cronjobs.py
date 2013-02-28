#!/usr/bin/env python
# Copyright 2010 Google Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""These aff4 objects are periodic cron jobs."""
import bisect
import datetime
import time
import traceback
import logging

from grr.lib import aff4
from grr.lib import data_store
from grr.lib import export_utils
from grr.lib import rdfvalue
from grr.lib import utils
from grr.proto import analysis_pb2


class CronJob(aff4.AFF4Object):
  """The baseclass of all cron jobs.

  Note: you should normally inherit from AbstractScheduledCronJob instead of
        this one.
  """

  # How often we should run in hours (Note this is a best effort attempt).
  frequency = 24.0

  class SchemaCls(aff4.AFF4Object.SchemaCls):
    LAST_RUN_TIME = aff4.Attribute(
        "aff4:cron/last_run", rdfvalue.RDFDatetime,
        "The last time this cron job ran.", "last_run", versioned=False)
    LOG = aff4.Attribute("aff4:log", rdfvalue.RDFString,
                         "Log messages related to the progress of this cron.")

  def DueToRun(self):
    """Called periodically by the cron daemon, if True Run() will be called.

    Returns:
        True if it is time to run based on the specified frequency.
    """
    last_run_time = self.Get(self.Schema.LAST_RUN_TIME)
    now = self.Schema.LAST_RUN_TIME()

    if (last_run_time is None or
        now - self.frequency * 60 * 60 * 1e6 > last_run_time):
      return True

    return False

  def Run(self):
    """Do the actual work of the Cron."""
    self.Set(self.Schema.LAST_RUN_TIME())   # Update LAST_RUN_TIME to now.

  def Log(self, message, level=logging.INFO, **kwargs):
    """Log a message to the cron's log attribute."""
    logging.log(level, message, **kwargs)
    # pylint: disable=W0212
    message = "%s: %s" % (logging._levelNames[level], message)
    self.AddAttribute(self.Schema.LOG(message))


class AbstractScheduledCronJob(CronJob):
  """CronJob that will be automatically run."""


class AbstractCronTask(CronJob):
  """A Cron sub task that is scheduled from another Cron."""


class Sample(rdfvalue.RDFProto):
  """A Graph sample is a single data point."""
  _proto = analysis_pb2.Sample


class Graph(rdfvalue.RDFProto):
  """A Graph is a collection of sample points."""
  _proto = analysis_pb2.Graph

  rdf_map = dict(data=Sample)

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
    now = rdfvalue.RDFDatetime()
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


class ClientStatsCronJob(AbstractScheduledCronJob):
  """A cron job which opens every client in the system.

  We feed all the client objects to the AbstractClientStatsCollector instances.
  """

  def Run(self):
    """Retrieve all the clients for the AbstractClientStatsCollectors."""
    # Instantiate all the depended cron jobs.
    super(ClientStatsCronJob, self).Run()
    jobs = []
    self.Log("Collecting ClientStatsCollectors that are due to run.")
    for cls_name, cls in self.classes.items():
      if aff4.issubclass(cls, AbstractClientStatsCollector):
        job = aff4.FACTORY.Create("cron:/%s" % cls_name, cls_name, mode="rw",
                                  token=self.token)
        if job.DueToRun():
          logging.info("%s: Will run %s", self.__class__.__name__, cls_name)
          job.Log("Starting cron job %s" % (cls_name))
          job.Run()  # Run will ensure LAST_RUN_TIME is updated.
          job.Start()
          jobs.append(job)
    self.Log("Collected %d ClientStatsCollectors. Starting run." % len(jobs))

    # Iterates over all the clients in the system, and feed them to the jobs.
    if jobs:
      root = aff4.FACTORY.Open(aff4.ROOT_URN, token=self.token)
      for child in root.OpenChildren(chunk_limit=100000):
        for job in jobs:
          job.ProcessClient(child)

      # Let the jobs know we are all done here.
      for job in jobs:
        job.Log("Successfully ran cron job %s" % (job.__class__.__name__))
        job.End()

  def DueToRun(self):
    """This job should always run."""
    return True


class AbstractClientStatsCollector(AbstractCronTask):
  """A base class for all jobs interested in all clients.

  The ClientStatsCronJob will open all the client objects and feed those to all
  derived classes for processing. This allows a single pass over all clients.
  """

  def ProcessClient(self, client):
    """This method will be called for each client in the system."""


class GRRVersionBreakDown(AbstractClientStatsCollector):
  """Records relative ratios of GRR versions in 7 day actives."""

  # Run every 4 hours.
  frequency = 4

  class SchemaCls(CronJob.SchemaCls):
    GRRVERSION_HISTOGRAM = aff4.Attribute("aff4:stats/grrversion", GraphSeries,
                                          "GRR version statistics for active "
                                          "clients.")

  def Start(self):
    self.counter = _ActiveCounter(self.Schema.GRRVERSION_HISTOGRAM)

  def End(self):
    self.counter.Save(self)
    self.Flush()

  def ProcessClient(self, client):
    ping = client.Get(client.Schema.PING)
    c_info = client.Get(client.Schema.CLIENT_INFO)
    if c_info and ping:
      category = " ".join([c_info.client_name,
                           str(c_info.client_version)])

      self.counter.Add(category, ping)


class OSBreakDown(AbstractClientStatsCollector):
  """Records relative ratios of OS versions in 7 day actives."""

  # Run every 24 hours.
  frequency = 24

  class SchemaCls(CronJob.SchemaCls):
    OS_HISTOGRAM = aff4.Attribute(
        "aff4:stats/os_type", GraphSeries,
        "Operating System statistics for active clients.")

    RELEASE_HISTOGRAM = aff4.Attribute("aff4:stats/release", GraphSeries,
                                       "Release statistics for active clients.")

    VERSION_HISTOGRAM = aff4.Attribute("aff4:stats/version", GraphSeries,
                                       "Version statistics for active clients.")

  def Start(self):
    self.counters = [
        _ActiveCounter(self.Schema.OS_HISTOGRAM),
        _ActiveCounter(self.Schema.VERSION_HISTOGRAM),
        _ActiveCounter(self.Schema.RELEASE_HISTOGRAM),
        ]

  def End(self):
    # Write all the counter attributes.
    for counter in self.counters:
      counter.Save(self)

    # Flush the data to the data store.
    self.Flush()

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


class LastAccessStats(AbstractClientStatsCollector):
  """Calculates a histogram statistics of clients last contacted times."""

  # The number of clients fall into these bins (number of hours ago)
  _bins = [1, 2, 3, 7, 14, 30, 60]

  # Run every 24 hours
  frequency = 24

  class SchemaCls(CronJob.SchemaCls):
    HISTOGRAM = aff4.Attribute("aff4:stats/last_contacted",
                               Graph, "Last contacted time")

  def Start(self):
    self._bins = [long(x*1e6*24*60*60) for x in self._bins]

    # We will count them in this bin
    self._value = [0] * len(self._bins)

  def End(self):
    # Build and store the graph now. Day actives are cumulative.
    cumulative_count = 0
    graph = self.Schema.HISTOGRAM()
    for x, y in zip(self._bins, self._value):
      cumulative_count += y
      graph.Append(x_value=x, y_value=cumulative_count)

    self.AddAttribute(graph)
    self.Flush()

  def ProcessClient(self, client):
    now = rdfvalue.RDFDatetime()

    ping = client.Get(client.Schema.PING)
    if ping:
      time_ago = now - ping
      pos = bisect.bisect(self._bins, time_ago)

      # If clients are older than the last bin forget them.
      try:
        self._value[pos] += 1
      except IndexError:
        pass




def RunAllCronJobs(token=None, override_frequency=None):
  """Search for all CronJobs and run them.

  Args:
    token: Auth token to use.
    override_frequency: Force the cron jobs to run at a different frequency.
        Defaults to None which uses the class specified value.
  """
  if override_frequency is not None:
    # Go through the ClientStatsCollectors changing them so they will run
    # on the override_frequency instead of default.
    for cls_name, cls in aff4.AFF4Object.classes.items():
      if aff4.issubclass(cls, AbstractClientStatsCollector):
        cls.frequency = int(override_frequency)

  for cls_name, cls in aff4.AFF4Object.classes.iteritems():
    if aff4.issubclass(cls, AbstractScheduledCronJob):
      # Create the job if it does not already exist.
      try:
        fd = aff4.FACTORY.Create("cron:/%s" % cls_name, cls_name, mode="rw",
                                 token=token)
      except IOError as e:
        logging.warn("Failed to open cron job %s", cls_name)
        continue

      if override_frequency is not None:
        fd.frequency = int(override_frequency)
      if not fd.DueToRun():   # Only run if schedule says we should.
        continue

      start_time = time.time()
      fd.Log("Running cron job %s" % cls_name)
      try:
        fd.Run()
        total_time = datetime.timedelta(seconds=int(time.time()-start_time))
        fd.Log("Successfully ran cron job %s in %s" % (cls_name, total_time))

      # Just keep going on all errors.
      except Exception as e:  # pylint: disable=W0703
        fd.Log("Cron Job %s died: %s" % (cls_name, e), level=logging.ERROR)
        fd.Log("Exception: %s" % traceback.format_exc())

      fd.Close()
