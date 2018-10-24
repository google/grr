#!/usr/bin/env python
"""Filestore stats crons."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


from future.utils import iteritems

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import stats as rdf_stats
from grr_response_core.lib.util import collection
from grr_response_server import aff4

from grr_response_server.aff4_objects import cronjobs
from grr_response_server.aff4_objects import stats as aff4_stats


class ClassCounter(object):
  """Populates a stats.Graph with counts of each object class."""

  def __init__(self, attribute, title):
    self.attribute = attribute
    self.value_dict = {}
    self.graph = self.attribute(title=title)

  def ProcessFile(self, fd):
    classname = fd.__class__.__name__
    self.value_dict[classname] = self.value_dict.get(classname, 0) + 1

  def Save(self, fd):
    for classname, count in iteritems(self.value_dict):
      self.graph.Append(label=classname, y_value=count)
    fd.Set(self.attribute, self.graph)


class ClassFileSizeCounter(ClassCounter):
  """Count total filesize by classtype."""

  GB = 1024 * 1024 * 1024

  def ProcessFile(self, fd):
    classname = fd.__class__.__name__
    self.value_dict[classname] = self.value_dict.get(classname, 0) + fd.Get(
        fd.Schema.SIZE)

  def Save(self, fd):
    for classname, count in iteritems(self.value_dict):
      self.graph.Append(label=classname, y_value=count / self.GB)
    fd.Set(self.attribute, self.graph)


class GraphDistribution(rdf_stats.Distribution):
  """Abstract class for building histograms."""

  _bins = []

  def __init__(self, attribute, title):
    self.attribute = attribute
    self.graph = self.attribute(title=title)
    super(GraphDistribution, self).__init__(bins=self._bins)

  def ProcessFile(self, fd):
    raise NotImplementedError()

  def Save(self, fd):
    for x, y in sorted(iteritems(self.bins_heights)):
      if x >= 0:
        self.graph.Append(x_value=int(x), y_value=y)

    fd.Set(self.attribute, self.graph)


class FileSizeHistogram(GraphDistribution):
  """Graph filesize."""

  _bins = [
      0, 2, 50, 100, 1e3, 10e3, 100e3, 500e3, 1e6, 5e6, 10e6, 50e6, 100e6,
      500e6, 1e9, 5e9, 10e9
  ]

  def ProcessFile(self, fd):
    self.Record(fd.Get(fd.Schema.SIZE))


class FilestoreStatsCronFlow(cronjobs.SystemCronFlow):
  """Build statistics about the filestore."""
  frequency = rdfvalue.Duration("1w")
  lifetime = rdfvalue.Duration("1d")
  HASH_PATH = "aff4:/files/hash/generic/sha256"
  FILESTORE_STATS_URN = rdfvalue.RDFURN("aff4:/stats/FileStoreStats")
  OPEN_FILES_LIMIT = 5000

  def _CreateConsumers(self):
    self.consumers = [
        ClassCounter(self.stats.Schema.FILESTORE_FILETYPES,
                     "Number of files in the filestore by type"),
        ClassFileSizeCounter(
            self.stats.Schema.FILESTORE_FILETYPES_SIZE,
            "Total filesize (GB) files in the filestore by type"),
        FileSizeHistogram(self.stats.Schema.FILESTORE_FILESIZE_HISTOGRAM,
                          "Filesize distribution in bytes"),
    ]

  def Start(self):
    """Retrieve all the clients for the AbstractClientStatsCollectors."""
    self.stats = aff4.FACTORY.Create(
        self.FILESTORE_STATS_URN,
        aff4_stats.FilestoreStats,
        mode="w",
        token=self.token)

    self._CreateConsumers()
    hashes = aff4.FACTORY.Open(
        self.HASH_PATH, token=self.token).ListChildren(limit=10**8)

    try:
      for urns in collection.Batch(hashes, self.OPEN_FILES_LIMIT):
        for fd in aff4.FACTORY.MultiOpen(
            urns, mode="r", token=self.token, age=aff4.NEWEST_TIME):

          for consumer in self.consumers:
            consumer.ProcessFile(fd)
        self.HeartBeat()

    finally:
      for consumer in self.consumers:
        consumer.Save(self.stats)
      self.stats.Close()
