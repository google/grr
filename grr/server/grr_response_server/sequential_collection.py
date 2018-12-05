#!/usr/bin/env python
"""A collection of records stored sequentially.

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import collections
import random
import threading
import time

from grr_response_core import config
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import registry
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_core.lib.util import precondition

from grr_response_server import data_store


class SequentialCollection(object):
  """A sequential collection of RDFValues.

  This class supports the writing of individual RDFValues and the sequential
  reading of them.

  """

  # The type which we store, subclasses must set this to a subclass of RDFValue.
  RDF_TYPE = None

  def __init__(self, collection_id):
    precondition.AssertType(collection_id, rdfvalue.RDFURN)

    super(SequentialCollection, self).__init__()
    # The collection_id for this collection is a RDFURN for now.
    self.collection_id = collection_id

  @classmethod
  def StaticAdd(cls,
                collection_urn,
                rdf_value,
                timestamp=None,
                suffix=None,
                mutation_pool=None):
    """Adds an rdf value to a collection.

    Adds an rdf value to a collection. Does not require that the collection be
    open. NOTE: The caller is responsible for ensuring that the collection
    exists and is of the correct type.

    Args:
      collection_urn: The urn of the collection to add to.
      rdf_value: The rdf value to add to the collection.
      timestamp: The timestamp (in microseconds) to store the rdf value at.
        Defaults to the current time.
      suffix: A 'fractional timestamp' suffix to reduce the chance of
        collisions. Defaults to a random number.
      mutation_pool: A MutationPool object to write to.

    Returns:
      The pair (timestamp, suffix) which identifies the value within the
      collection.

    Raises:
      ValueError: rdf_value has unexpected type.

    """
    if not isinstance(rdf_value, cls.RDF_TYPE):
      raise ValueError("This collection only accepts values of type %s." %
                       cls.RDF_TYPE.__name__)
    if mutation_pool is None:
      raise ValueError("Mutation pool can't be none.")
    if timestamp is None:
      timestamp = rdfvalue.RDFDatetime.Now()
    if isinstance(timestamp, rdfvalue.RDFDatetime):
      timestamp = timestamp.AsMicrosecondsSinceEpoch()

    if not rdf_value.age:
      rdf_value.age = rdfvalue.RDFDatetime.Now()

    if not isinstance(collection_urn, rdfvalue.RDFURN):
      collection_urn = rdfvalue.RDFURN(collection_urn)

    _, timestamp, suffix = mutation_pool.CollectionAddItem(
        collection_urn, rdf_value, timestamp, suffix=suffix)

    return timestamp, suffix

  def Add(self, rdf_value, timestamp=None, suffix=None, mutation_pool=None):
    """Adds an rdf value to the collection.

    Adds an rdf value to the collection. Does not require that the collection
    be locked.

    Args:
      rdf_value: The rdf value to add to the collection.
      timestamp: The timestamp (in microseconds) to store the rdf value at.
        Defaults to the current time.
      suffix: A 'fractional timestamp' suffix to reduce the chance of
        collisions. Defaults to a random number.
      mutation_pool: A MutationPool object to write to.

    Returns:
      The pair (timestamp, suffix) which identifies the value within the
      collection.

    Raises:
      ValueError: rdf_value has unexpected type.

    """
    return self.StaticAdd(
        self.collection_id,
        rdf_value,
        timestamp=timestamp,
        suffix=suffix,
        mutation_pool=mutation_pool)

  def Scan(self, after_timestamp=None, include_suffix=False, max_records=None):
    """Scans for stored records.

    Scans through the collection, returning stored values ordered by timestamp.

    Args:
      after_timestamp: If set, only returns values recorded after timestamp.
      include_suffix: If true, the timestamps returned are pairs of the form
        (micros_since_epoc, suffix) where suffix is a 24 bit random refinement
        to avoid collisions. Otherwise only micros_since_epoc is returned.
      max_records: The maximum number of records to return. Defaults to
        unlimited.

    Yields:
      Pairs (timestamp, rdf_value), indicating that rdf_value was stored at
      timestamp.

    """
    suffix = None
    if isinstance(after_timestamp, tuple):
      suffix = after_timestamp[1]
      after_timestamp = after_timestamp[0]

    for item, timestamp, suffix in data_store.DB.CollectionScanItems(
        self.collection_id,
        self.RDF_TYPE,
        after_timestamp=after_timestamp,
        after_suffix=suffix,
        limit=max_records):
      if include_suffix:
        yield ((timestamp, suffix), item)
      else:
        yield (timestamp, item)

  def MultiResolve(self, records):
    """Lookup multiple values by their record objects."""
    for value, timestamp in data_store.DB.CollectionReadItems(records):
      rdf_value = self.RDF_TYPE.FromSerializedString(value)
      rdf_value.age = timestamp
      yield rdf_value

  def __iter__(self):
    for _, item in self.Scan():
      yield item

  def Delete(self):
    pool = data_store.DB.GetMutationPool()
    with pool:
      pool.CollectionDelete(self.collection_id)


class BackgroundIndexUpdater(object):
  """Updates IndexedSequentialCollection objects in the background."""
  INDEX_DELAY = 240

  exit_now = False

  def __init__(self):
    self.to_process = collections.deque()
    self.cv = threading.Condition()

  def ExitNow(self):
    with self.cv:
      self.exit_now = True
      self.to_process.append(None)
      self.cv.notify()

  def AddIndexToUpdate(self, collection_cls, index_urn):
    with self.cv:
      self.to_process.append((collection_cls, index_urn,
                              time.time() + self.INDEX_DELAY))
      self.cv.notify()

  def ProcessCollection(self, collection_cls, collection_id):
    collection_cls(collection_id).UpdateIndex()

  def UpdateLoop(self):
    """Main loop that usually never terminates."""
    while not self.exit_now:
      with self.cv:
        while not self.to_process:
          self.cv.wait()
        next_update = self.to_process.popleft()
        if next_update is None:
          return

      now = time.time()
      next_cls = next_update[0]
      next_urn = next_update[1]
      next_time = next_update[2]
      while now < next_time and not self.exit_now:
        time.sleep(1)
        now = time.time()

      self.ProcessCollection(next_cls, next_urn)


BACKGROUND_INDEX_UPDATER = BackgroundIndexUpdater()


class UpdaterStartHook(registry.InitHook):
  """Init hook to start the background index updater."""

  def RunOnce(self):
    in_test = u"Test Context" in config.CONFIG.context
    if in_test:
      # Don't start the index updater in tests.
      return

    t = threading.Thread(
        target=BACKGROUND_INDEX_UPDATER.UpdateLoop,
        name="SequentialCollectionIndexUpdater")
    t.daemon = True
    t.start()


class IndexedSequentialCollection(SequentialCollection):
  """An indexed sequential collection of RDFValues.

  Adds an index to SequentialCollection, making it efficient to find the number
  of records present, and to find a particular record number.

  IMPLEMENTATION NOTE: The index is created lazily, and for records older than
    INDEX_WRITE_DELAY.
  """

  # How many records between index entries. Subclasses may change this.  The
  # full index must fit comfortably in RAM, default is meant to be reasonable
  # for collections of up to ~1b small records. (Assumes we can have ~1m index
  # points in ram, and that reading 1k records is reasonably fast.)

  INDEX_SPACING = 1024

  # An attribute name of the form "index:sc_<i>" at timestamp <t> indicates that
  # the item with record number i was stored at timestamp t. The timestamp
  # suffix is stored as the value.

  INDEX_ATTRIBUTE_PREFIX = "index:sc_"

  # The time to wait before creating an index for a record - hacky defense
  # against the correct index changing due to a late write.

  INDEX_WRITE_DELAY = rdfvalue.Duration("3m")

  def __init__(self, *args, **kwargs):
    super(IndexedSequentialCollection, self).__init__(*args, **kwargs)
    self._index = None

  def _ReadIndex(self):
    if self._index:
      return
    self._index = {0: (0, 0)}
    self._max_indexed = 0
    for (index, ts,
         suffix) in data_store.DB.CollectionReadIndex(self.collection_id):
      self._index[index] = (ts, suffix)
      self._max_indexed = max(index, self._max_indexed)

  def _MaybeWriteIndex(self, i, ts, mutation_pool):
    """Write index marker i."""
    if i > self._max_indexed and i % self.INDEX_SPACING == 0:
      # We only write the index if the timestamp is more than 5 minutes in the
      # past: hacky defense against a late write changing the count.
      if ts[0] < (rdfvalue.RDFDatetime.Now() -
                  self.INDEX_WRITE_DELAY).AsMicrosecondsSinceEpoch():
        mutation_pool.CollectionAddIndex(self.collection_id, i, ts[0], ts[1])
        self._index[i] = ts
        self._max_indexed = max(i, self._max_indexed)

  def _IndexedScan(self, i, max_records=None):
    """Scan records starting with index i."""
    self._ReadIndex()

    # The record number that we will read next.
    idx = 0
    # The timestamp that we will start reading from.
    start_ts = 0
    if i >= self._max_indexed:
      start_ts = max((0, 0), (self._index[self._max_indexed][0],
                              self._index[self._max_indexed][1] - 1))
      idx = self._max_indexed
    else:
      try:
        possible_idx = i - i % self.INDEX_SPACING
        start_ts = (max(0, self._index[possible_idx][0]),
                    self._index[possible_idx][1] - 1)
        idx = possible_idx
      except KeyError:
        pass

    if max_records is not None:
      max_records += i - idx

    with data_store.DB.GetMutationPool() as mutation_pool:
      for (ts, value) in self.Scan(
          after_timestamp=start_ts,
          max_records=max_records,
          include_suffix=True):
        self._MaybeWriteIndex(idx, ts, mutation_pool)
        if idx >= i:
          yield (idx, ts, value)
        idx += 1

  def GenerateItems(self, offset=0):
    for (_, _, value) in self._IndexedScan(offset):
      yield value

  def __getitem__(self, index):
    if index >= 0:
      for (_, _, value) in self._IndexedScan(index, max_records=1):
        return value
      raise IndexError("collection index out of range")
    else:
      raise RuntimeError("Index must be >= 0")

  def CalculateLength(self):
    self._ReadIndex()
    highest_index = None
    for (i, _, _) in self._IndexedScan(self._max_indexed):
      highest_index = i
    if highest_index is None:
      return 0
    return highest_index + 1

  def __len__(self):
    return self.CalculateLength()

  def UpdateIndex(self):
    self._ReadIndex()
    for _ in self._IndexedScan(self._max_indexed):
      pass

  @classmethod
  def StaticAdd(cls,
                collection_urn,
                rdf_value,
                timestamp=None,
                suffix=None,
                mutation_pool=None):
    r = super(IndexedSequentialCollection, cls).StaticAdd(
        collection_urn,
        rdf_value,
        timestamp=timestamp,
        suffix=suffix,
        mutation_pool=mutation_pool)
    if not isinstance(collection_urn, rdfvalue.RDFURN):
      collection_urn = rdfvalue.RDFURN(collection_urn)

    if random.randint(0, cls.INDEX_SPACING) == 0:
      BACKGROUND_INDEX_UPDATER.AddIndexToUpdate(cls, collection_urn)
    return r


class GeneralIndexedCollection(IndexedSequentialCollection):
  """An indexed sequential collection of RDFValues with different types."""
  RDF_TYPE = rdf_protodict.EmbeddedRDFValue

  @classmethod
  def StaticAdd(cls,
                collection_urn,
                rdf_value,
                timestamp=None,
                suffix=None,
                mutation_pool=None):
    if not rdf_value.age:
      rdf_value.age = rdfvalue.RDFDatetime.Now()

    super(GeneralIndexedCollection, cls).StaticAdd(
        collection_urn,
        rdf_protodict.EmbeddedRDFValue(payload=rdf_value),
        timestamp=timestamp,
        suffix=suffix,
        mutation_pool=mutation_pool)

  def Scan(self, **kwargs):
    for (timestamp, rdf_value) in super(GeneralIndexedCollection,
                                        self).Scan(**kwargs):
      yield (timestamp, rdf_value.payload)


class GrrMessageCollection(IndexedSequentialCollection):
  """Sequential HuntResultCollection."""
  RDF_TYPE = rdf_flows.GrrMessage

  def AddAsMessage(self, rdfvalue_in, source, mutation_pool=None):
    """Helper method to add rdfvalues as GrrMessages for testing."""
    self.Add(
        rdf_flows.GrrMessage(payload=rdfvalue_in, source=source),
        mutation_pool=mutation_pool)
