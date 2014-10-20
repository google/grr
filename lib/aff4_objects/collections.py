#!/usr/bin/env python
"""Implementations of various collections."""



import cStringIO
import struct

import logging

from grr.lib import aff4
from grr.lib import data_store
from grr.lib import rdfvalue
from grr.lib import utils
from grr.lib.aff4_objects import aff4_grr


class RDFValueCollection(aff4.AFF4Object):
  """This is a collection of RDFValues."""
  # If this is set to an RDFValue class implementation, all the contained
  # objects must be instances of this class.
  _rdf_type = None

  _behaviours = set()
  size = 0

  # The file object for the underlying AFF4Image stream.
  fd = None

  class SchemaCls(aff4.AFF4Object.SchemaCls):
    SIZE = aff4.AFF4Stream.SchemaCls.SIZE

    DESCRIPTION = aff4.Attribute("aff4:description", rdfvalue.RDFString,
                                 "This collection's description", "description")

    VIEW = aff4.Attribute("aff4:rdfview", aff4_grr.RDFValueCollectionView,
                          "The list of attributes which will show up in "
                          "the table.", default="")

  def Initialize(self):
    """Initialize the internal storage stream."""
    self.stream_dirty = False

    try:
      self.fd = aff4.FACTORY.Open(self.urn.Add("Stream"),
                                  aff4_type="AFF4Image", mode=self.mode,
                                  token=self.token)
      self.size = int(self.Get(self.Schema.SIZE))

      return
    except IOError:
      pass

    # If we get here, the stream does not already exist - we create a new
    # stream.
    self.fd = aff4.FACTORY.Create(self.urn.Add("Stream"), "AFF4Image",
                                  mode=self.mode, token=self.token)
    self.fd.seek(0, 2)
    self.size = 0

  def SetChunksize(self, chunk_size):

    if self.fd.size != 0:
      raise ValueError("Cannot set chunk size on an existing collection.")
    self.fd.SetChunksize(chunk_size)

  def Flush(self, sync=False):
    if self.stream_dirty:
      self.Set(self.Schema.SIZE(self.size))
      self.fd.Flush(sync=sync)

    super(RDFValueCollection, self).Flush(sync=sync)

  def Close(self, sync=False):
    self.Flush(sync=sync)

  def Add(self, rdf_value=None, **kwargs):
    """Add the rdf value to the collection."""
    if rdf_value is None:
      if self._rdf_type:
        rdf_value = self._rdf_type(**kwargs)  # pylint: disable=not-callable
      else:
        raise ValueError("RDFValueCollection doesn't accept None values.")

    if self._rdf_type and not isinstance(rdf_value, self._rdf_type):
      raise ValueError("This collection only accepts values of type %s" %
                       self._rdf_type.__name__)

    if not rdf_value.age:
      rdf_value.age.Now()

    data = rdfvalue.EmbeddedRDFValue(payload=rdf_value).SerializeToString()
    self.fd.Seek(0, 2)
    self.fd.Write(struct.pack("<i", len(data)))
    self.fd.Write(data)
    self.stream_dirty = True

    self.size += 1

  def AddAll(self, rdf_values, callback=None):
    """Adds a list of rdfvalues to the collection."""
    for rdf_value in rdf_values:
      if rdf_value is None:
        raise ValueError("Can't add None to the collection via AddAll.")

      if self._rdf_type and not isinstance(rdf_value, self._rdf_type):
        raise ValueError("This collection only accepts values of type %s" %
                         self._rdf_type.__name__)

      if not rdf_value.age:
        rdf_value.age.Now()

    buf = cStringIO.StringIO()
    for index, rdf_value in enumerate(rdf_values):
      data = rdfvalue.EmbeddedRDFValue(payload=rdf_value).SerializeToString()
      buf.write(struct.pack("<i", len(data)))
      buf.write(data)

      self.size += 1
      if callback:
        callback(index, rdf_value)

    self.fd.Seek(0, 2)
    self.fd.Write(buf.getvalue())
    self.stream_dirty = True

  def __len__(self):
    return self.size

  def __nonzero__(self):
    return self.size != 0

  def __iter__(self):
    """Iterate over all contained RDFValues.

    Returns:
      Generator of RDFValues stored in the collection.

    Raises:
      RuntimeError: if we are in write mode.
    """
    return self.GenerateItems()

  @property
  def current_offset(self):
    return self.fd.Tell()

  def GenerateItems(self, offset=0):
    """Iterate over all contained RDFValues.

    Args:
      offset: The offset in the stream to start reading from.

    Yields:
      RDFValues stored in the collection.

    Raises:
      RuntimeError: if we are in write mode.
    """
    if not self.fd:
      return

    if self.mode == "w":
      raise RuntimeError("Can not read when in write mode.")

    self.fd.seek(offset)
    count = 0

    while True:
      offset = self.fd.Tell()
      try:
        length = struct.unpack("<i", self.fd.Read(4))[0]
        serialized_event = self.fd.Read(length)
      except struct.error:
        break

      result = rdfvalue.EmbeddedRDFValue(serialized_event)

      payload = result.payload
      if payload is not None:
        # Mark the RDFValue with important information relating to the
        # collection it is from.
        payload.id = count
        payload.collection_offset = offset

        yield payload
      else:
        logging.warning("payload=None was encountered in a collection %s "
                        "(index %d), this may mean a logical bug or corrupt "
                        "data. Ignoring...", self.urn, count)

      count += 1

  def GetItem(self, offset=0):
    for item in self.GenerateItems(offset=offset):
      return item

  def __getitem__(self, index):
    if index >= 0:
      for i, item in enumerate(self):
        if i == index:
          return item
    else:
      raise RuntimeError("Index must be >= 0")


class AFF4Collection(aff4.AFF4Volume, RDFValueCollection):
  """A collection of AFF4 objects.

  The AFF4 objects themselves are opened on demand from the data store. The
  collection simply stores the RDFURNs of all aff4 objects in the collection.
  """

  _rdf_type = rdfvalue.AFF4ObjectSummary

  _behaviours = frozenset(["Collection"])

  class SchemaCls(aff4.AFF4Volume.SchemaCls, RDFValueCollection.SchemaCls):
    VIEW = aff4.Attribute("aff4:view", rdfvalue.AFF4CollectionView,
                          "The list of attributes which will show up in "
                          "the table.", default="")

  def CreateView(self, attributes):
    """Given a list of attributes, update our view.

    Args:
      attributes: is a list of attribute names.
    """
    self.Set(self.Schema.VIEW(attributes))

  def Query(self, filter_string="", subjects=None, limit=100):
    """Filter the objects contained within this collection."""
    if subjects is None:
      subjects = set()
      for obj in self:
        if len(subjects) < limit:
          subjects.add(obj.urn)
        else:
          break

    else:
      subjects = set(subjects[:limit])

    if filter_string:
      # Parse the query string
      ast = aff4.AFF4QueryParser(filter_string).Parse()

      # Query our own data store
      filter_obj = ast.Compile(aff4.AFF4Filter)

    # We expect RDFURN objects to be stored in this collection.
    for subject in aff4.FACTORY.MultiOpen(subjects, token=self.token):
      if filter_string and not filter_obj.FilterOne(subject):
        continue

      yield subject

  def ListChildren(self, **_):
    for aff4object_summary in self:
      yield aff4object_summary.urn


class GRRSignedBlobCollection(RDFValueCollection):
  _rdf_type = rdfvalue.SignedBlob


class GRRSignedBlob(aff4.AFF4MemoryStream):
  """A container for storing a signed binary blob such as a driver."""

  def Initialize(self):
    self.collection = aff4.FACTORY.Create(
        self.urn.Add("collection"), "GRRSignedBlobCollection", mode=self.mode,
        token=self.token)
    self.fd = cStringIO.StringIO()

    if "r" in self.mode:
      for x in self.collection:
        self.fd.write(x.data)

      self.size = self.fd.tell()
      self.fd.seek(0)

    # How many chunks we have?
    self.chunks = len(self.collection)

  def Add(self, item):
    self.collection.Add(item)

  def __iter__(self):
    return iter(self.collection)

  def Close(self):
    super(GRRSignedBlob, self).Close()
    self.collection.Close()


class GRRMemoryDriver(GRRSignedBlob):
  """A driver for acquiring memory."""

  class SchemaCls(GRRSignedBlob.SchemaCls):
    INSTALLATION = aff4.Attribute(
        "aff4:driver/installation", rdfvalue.DriverInstallTemplate,
        "The driver installation control protobuf.", "installation",
        default=rdfvalue.DriverInstallTemplate(
            driver_name="pmem", device_path=r"\\.\pmem"))


class GrepResultsCollection(RDFValueCollection):
  """A collection of grep results."""
  _rdf_type = rdfvalue.BufferReference


class ClientAnomalyCollection(RDFValueCollection):
  """A collection of anomalies related to a client.

  This class is a normal collection, but with additional methods for making
  viewing and working with anomalies easier.
  """
  _rdf_type = rdfvalue.Anomaly


# DEPRECATED: this class is deprecated and is left here only temporary for
# compatibility reasons. Add method raises a RuntimeError to discourage
# further use of this class. Please use PackedVersionedCollection instead:
# it has same functionality and better performance characterstics.
class VersionedCollection(RDFValueCollection):
  """DEPRECATED: A collection which uses the data store's version properties.

  This collection is very efficient for writing to - we can insert new values by
  blind writing them into the data store without needing to take a lock - using
  the timestamping features of the data store.
  """

  class SchemaCls(RDFValueCollection.SchemaCls):
    DATA = aff4.Attribute("aff4:data", rdfvalue.EmbeddedRDFValue,
                          "The embedded semantic value.", versioned=True)

  def Add(self, rdf_value=None, **kwargs):
    """Add the rdf value to the collection."""
    raise RuntimeError("VersionedCollection is deprecated, can't add new "
                       "elements.")

  def AddAll(self, rdf_values, callback=None):
    """Add multiple rdf values to the collection."""
    raise RuntimeError("VersionedCollection is deprecated, can't add new "
                       "elements.")

  def GenerateItems(self, offset=None, timestamp=None):
    if offset is not None and timestamp is not None:
      raise ValueError("Either offset or timestamp can be specified.")

    if timestamp is None:
      timestamp = data_store.DB.ALL_TIMESTAMPS

    index = 0
    for _, value, ts in data_store.DB.ResolveMulti(
        self.urn, [self.Schema.DATA.predicate], token=self.token,
        timestamp=timestamp):
      if index >= offset:
        yield self.Schema.DATA(value, age=ts).payload
      index += 1


class PackedVersionedCollection(RDFValueCollection):
  """A collection which uses the data store's version properties.

  This collection is very efficient for writing to - we can insert new values by
  blind writing them into the data store - using the timestamping features of
  the data store.

  Unfortunately reading from versioned data store attributes is slow. Therefore
  this object implements a compaction strategy, where writes are versioned,
  until they can be compacted into a regular RDFValueCollection by the
  VersionedCollectionCompactor cron job.
  """

  class SchemaCls(RDFValueCollection.SchemaCls):
    DATA = aff4.Attribute("aff4:data", rdfvalue.EmbeddedRDFValue,
                          "The embedded semantic value.", versioned=True)

  COMPACTION_BATCH_SIZE = 10000
  MAX_REVERSED_RESULTS = 10000

  def Add(self, rdf_value=None, **kwargs):
    """Add the rdf value to the collection."""
    if rdf_value is None and self._rdf_type:
      rdf_value = self._rdf_type(**kwargs)  # pylint: disable=not-callable

    if not rdf_value.age:
      rdf_value.age.Now()

    self.Set(self.Schema.DATA(payload=rdf_value))

    # Let the compactor know we need compacting.
    data_store.DB.Set("aff4:/cron/versioned_collection_compactor",
                      "index:changed/%s" % self.urn, self.urn,
                      replace=True, token=self.token, sync=False)

  def AddAll(self, rdf_values, callback=None):
    """Adds a list of rdfvalues to the collection."""
    for rdf_value in rdf_values:
      if rdf_value is None:
        raise ValueError("Can't add None to the collection via AddAll.")

      if self._rdf_type and not isinstance(rdf_value, self._rdf_type):
        raise ValueError("This collection only accepts values of type %s" %
                         self._rdf_type.__name__)

      if not rdf_value.age:
        rdf_value.age.Now()

    for index, rdf_value in enumerate(rdf_values):
      self.Set(self.Schema.DATA(payload=rdf_value))
      if callback:
        callback(index, rdf_value)

    # Let the compactor know we need compacting.
    data_store.DB.Set("aff4:/cron/versioned_collection_compactor",
                      "index:changed/%s" % self.urn, self.urn,
                      replace=True, token=self.token, sync=False)

  def GenerateItems(self, offset=0):
    """First iterate over the versions, and then iterate over the stream."""
    index = 0

    for x in super(PackedVersionedCollection, self).GenerateItems():
      if index >= offset:
        yield x
      index += 1

    if self.IsAttributeSet(self.Schema.DATA):
      results = []
      for _, value, _ in data_store.DB.ResolveRegex(
          self.urn, self.Schema.DATA.predicate, token=self.token,
          timestamp=data_store.DB.ALL_TIMESTAMPS):
        if index >= offset:
          if results is not None:
            results.append(self.Schema.DATA(value).payload)
            if len(results) > self.MAX_REVERSED_RESULTS:
              for result in results:
                yield result
              results = None
          else:
            yield self.Schema.DATA(value).payload

        index += 1

      if results is not None:
        for result in reversed(results):
          yield result

  @utils.Synchronized
  def Compact(self, callback=None):
    """Compacts versioned attributes into the collection stream.

    Versioned attributes come from the datastore sorted by the timestamp
    in the decreasing order. This is the opposite of what we want in
    the collection (as items in the collection should be in chronological
    order).

    Compact's implementation can handle very large collections that can't
    be reversed in memory. It reads them in batches, reverses every batch
    individually, and then reads batches back in the reversed order and
    write their contents to the collection stream.

    Args:
      callback: An optional function without arguments that gets called
                periodically while processing is done. Useful in flows
                that have to heartbeat.

    Raises:
      RuntimeError: if problems are encountered when reading back temporary
                    saved data.

    Returns:
      Number of compacted results.
    """
    compacted_count = 0

    batches_urns = []
    current_batch = []

    # This timestamp will be used to delete attributes. We don't want
    # to delete anything that was added after we started the compaction.
    freeze_timestamp = rdfvalue.RDFDatetime().Now()

    def DeleteVersionedDataAndFlush():
      """Removes versioned attributes and flushes the stream."""
      data_store.DB.DeleteAttributes(self.urn, [self.Schema.DATA.predicate],
                                     end=freeze_timestamp,
                                     token=self.token, sync=True)

      if self.Schema.DATA in self.synced_attributes:
        del self.synced_attributes[self.Schema.DATA]

      self.size += compacted_count
      self.Flush(sync=True)

    # We over all versioned attributes. If we get more than
    # self.COMPACTION_BATCH_SIZE, we write the data to temporary
    # stream in the reversed order.
    for _, value, _ in data_store.DB.ResolveRegex(
        self.urn, self.Schema.DATA.predicate, token=self.token,
        timestamp=(0, freeze_timestamp)):

      if callback:
        callback()

      current_batch.append(value)
      compacted_count += 1

      if len(current_batch) >= self.COMPACTION_BATCH_SIZE:
        batch_urn = rdfvalue.RDFURN("aff4:/tmp").Add(
            "%X" % utils.PRNG.GetULong())
        batches_urns.append(batch_urn)

        buf = cStringIO.StringIO()
        for data in reversed(current_batch):
          buf.write(struct.pack("<i", len(data)))
          buf.write(data)

        # We use AFF4Image to avoid serializing/deserializing data stored
        # in versioned attributes.
        with aff4.FACTORY.Create(batch_urn, "AFF4Image", mode="w",
                                 token=self.token) as batch_stream:
          batch_stream.Write(buf.getvalue())

        current_batch = []

    # If there are no versioned attributes, we have nothing to do.
    if not current_batch and not batches_urns:
      return 0

    # The last batch of results can be written to our collection's stream
    # immediately, because we have to reverse the order of all the data
    # stored in versioned attributes.
    if current_batch:
      buf = cStringIO.StringIO()
      for data in reversed(current_batch):
        buf.write(struct.pack("<i", len(data)))
        buf.write(data)

      self.fd.Seek(0, 2)
      self.fd.Write(buf.getvalue())
      self.stream_dirty = True

      # If current_batch was the only available batch, just write everything
      # and return.
      if not batches_urns:
        DeleteVersionedDataAndFlush()
        return compacted_count

    batches = {}
    for batch in aff4.FACTORY.MultiOpen(batches_urns, aff4_type="AFF4Image",
                                        token=self.token):
      batches[batch.urn] = batch

    if len(batches_urns) != len(batches):
      raise RuntimeError("Internal inconsistency can't read back all the "
                         "temporary batches.")

    # We read all the temporary batches in reverse order (batches itself
    # were reversed when they were written).
    self.fd.Seek(0, 2)
    for batch_urn in reversed(batches_urns):
      batch = batches[batch_urn]

      if callback:
        callback()

      data = batch.Read(len(batch))
      self.fd.Write(data)
      self.stream_dirty = True

      aff4.FACTORY.Delete(batch_urn, token=self.token)

    DeleteVersionedDataAndFlush()
    return compacted_count

  def CalculateLength(self):
    length = super(PackedVersionedCollection, self).__len__()

    if self.IsAttributeSet(self.Schema.DATA):
      if self.age_policy == aff4.ALL_TIMES:
        length += len(list(self.GetValuesForAttribute(self.Schema.DATA)))
      else:
        length += len(list(data_store.DB.ResolveMulti(
            self.urn, [self.Schema.DATA.predicate], token=self.token,
            timestamp=data_store.DB.ALL_TIMESTAMPS)))

    return length

  @property
  def current_offset(self):
    raise AttributeError("current_offset is called on a "
                         "PackedVersionedCollection, this will not work.")

  def __len__(self):
    raise AttributeError(
        "Len called on a PackedVersionedCollection, this will not work.")

  def __nonzero__(self):
    if "r" not in self.mode:
      raise AttributeError(
          "Cannot determine collection length in write only mode.")

    # This checks if there is data in the stream.
    if super(PackedVersionedCollection, self).__nonzero__():
      return True

    # if there is not, we might have some uncompacted data.
    return self.IsAttributeSet(self.Schema.DATA)
