#!/usr/bin/env python
#
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
import logging

from grr.lib import aff4
from grr.lib import data_store
from grr.proto import analysis_pb2


class CronJob(aff4.AFF4Object):
  """The baseclass of all cron jobs."""

  # How often we should run in hours (Note this is a best effort attempt).
  frequency = 24.0

  class SchemaCls(aff4.AFF4Object.SchemaCls):
    LAST_RUN_TIME = aff4.Attribute(
        "aff4:cron/last_run", aff4.RDFDatetime,
        "The last time this cron job ran.", "last_run")

  def Run(self):
    """This method gets called periodically by the cron daemon.

    Returns:
        True if it is time to run based on the specified frequency.
    """
    last_run_time = self.Get(self.Schema.LAST_RUN_TIME)
    now = self.Schema.LAST_RUN_TIME()

    if (last_run_time is None or
        now - self.frequency * 60 * 60 * 1e6 > last_run_time):
      # Touch up our last run time
      self.Set(now)
      logging.info("Running cron job %s", self.__class__.__name__)
      return True

    return False


class Graph(aff4.RDFProto):
  _proto = analysis_pb2.Graph


class GraphSeries(aff4.RDFProtoArray):
  """A sequence of graphs (e.g. evolving over time)."""
  _proto = analysis_pb2.Graph


class _ActiveCounter(object):
  """A helper class to count the number of times a specific category occured."""

  active_days = [1, 7, 14, 30]

  def __init__(self, attribute):
    self.attribute = attribute
    self.categories = dict([(x, {}) for x in self.active_days])

  def Add(self, category, age):
    now = aff4.RDFDatetime()

    for active_time in self.active_days:
      if now - age < active_time * 24 * 60 * 60 * 1e6:
        self.categories[active_time][category] = self.categories[
            active_time].get(category, 0) + 1

  def Save(self, fd):
    histogram = self.attribute()
    for active_time in self.active_days:
      graph = analysis_pb2.Graph(title="%s day actives" % active_time)
      for k, v in self.categories[active_time].items():
        graph.data.add(label=k, y_value=v)

      histogram.data.append(graph)

    fd.AddAttribute(histogram)


class OSBreakDown(CronJob):
  """Records relative ratios of OS versions in 7 day actives."""

  frequency = 0

  class SchemaCls(CronJob.SchemaCls):
    OS_HISTOGRAM = aff4.Attribute(
        "aff4:stats/os_type", GraphSeries,
        "Operating System statistics for active clients.")

    RELEASE_HISTOGRAM = aff4.Attribute("aff4:stats/release", GraphSeries,
                                       "Release statistics for active clients.")

    VERSION_HISTOGRAM = aff4.Attribute("aff4:stats/version", GraphSeries,
                                       "Release statistics for active clients.")

  def Run(self):
    if super(OSBreakDown, self).Run():
      # Use the clock attribute as the last checked in time.
      predicates = [
          aff4.Attribute.GetAttributeByName("System").predicate,
          aff4.Attribute.GetAttributeByName("Version").predicate,
          aff4.Attribute.GetAttributeByName("Release").predicate,
          aff4.Attribute.GetAttributeByName("Clock").predicate]

      counters = [
          _ActiveCounter(self.Schema.OS_HISTOGRAM),
          _ActiveCounter(self.Schema.VERSION_HISTOGRAM),
          _ActiveCounter(self.Schema.RELEASE_HISTOGRAM),
          ]

      for row in data_store.DB.Query(
          predicates, data_store.DB.Filter.HasPredicateFilter(predicates[0]),
          limit=1e6, token=self.token):

        category = []
        for i, counter in enumerate(counters):
          # Take the age from the clock attribute as representative of the
          # active time.
          _, age = row[predicates[3]]
          value, _ = row[predicates[i]]
          category.append(value)
          counter.Add(",".join(category), age)

      for counter in counters:
        counter.Save(self)


class LastAccessStats(CronJob):
  """Calculates a histogram statistics of clients last contacted times."""

  # The number of clients fall into these bins (number of hours ago)
  _bins = [1, 2, 3, 7, 14, 30, 60]

  # Run every 24 hours
  frequency = 24

  class SchemaCls(CronJob.SchemaCls):
    HISTOGRAM = aff4.Attribute("aff4:stats/last_contacted",
                               Graph, "Last contacted time")

  def Run(self):
    if super(LastAccessStats, self).Run():
      now = aff4.RDFDatetime()

      # Change the bins to be in microseconds
      bins = [long(x*1e6*24*60*60) for x in self._bins]

      # We will count them in this bin
      self._value = [0] * len(self._bins)

      # Use the clock attribute as the last checked in time.
      predicate = aff4.Attribute.GetAttributeByName("Clock").predicate

      for row in data_store.DB.Query(
          [predicate], data_store.DB.Filter.HasPredicateFilter(predicate),
          limit=1e6, token=self.token):

        # We just use the age of the attribute
        _, age = row[predicate]
        time_ago = now - age

        pos = bisect.bisect(bins, time_ago)
        # If clients are older than the last bin forget them.
        try:
          self._value[pos] += 1
        except IndexError:
          pass

      # Build and store the graph now. Day actives are cumulative.
      cumulative_count = 0
      graph = self.Schema.HISTOGRAM()
      for x, y in zip(self._bins, self._value):
        cumulative_count += y
        graph.data.data.add(x_value=x, y_value=cumulative_count)

      self.AddAttribute(graph)
