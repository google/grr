#!/usr/bin/env python
"""Implementations of various collections."""



import cStringIO
import itertools
import struct

import logging

from grr.lib import aff4
from grr.lib import config_lib
from grr.lib import data_store
from grr.lib import rdfvalue
from grr.lib import registry
from grr.lib import stats
from grr.lib import utils
from grr.lib.rdfvalues import anomaly as rdf_anomaly
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import crypto as rdf_crypto
from grr.lib.rdfvalues import flows as rdf_flows
from grr.lib.rdfvalues import protodict as rdf_protodict
from grr.lib.rdfvalues import structs as rdf_structs
from grr.proto import jobs_pb2


class ComponentObject(aff4.AFF4Object):
  """An object holding a component."""

  class SchemaCls(aff4.AFF4Object.SchemaCls):
    COMPONENT = aff4.Attribute("aff4:component",
                               rdf_client.ClientComponentSummary,
                               "The component of the client.")


class AFF4CollectionView(rdf_protodict.RDFValueArray):
  """A view specifies how an AFF4Collection is seen."""


class RDFValueCollectionView(rdf_protodict.RDFValueArray):
  """A view specifies how an RDFValueCollection is seen."""


class RDFValueCollection(aff4.AFF4Object):
  """This is a collection of RDFValues."""
  # If this is set to an RDFValue class implementation, all the contained
  # objects must be instances of this class.
  _rdf_type = None

  _behaviours = set()
  _size = 0

  # The file object for the underlying AFF4Image stream.
  _fd = None

  class SchemaCls(aff4.AFF4Object.SchemaCls):
    SIZE = aff4.AFF4Stream.SchemaCls.SIZE

    DESCRIPTION = aff4.Attribute("aff4:description", rdfvalue.RDFString,
                                 "This collection's description", "description")

    VIEW = aff4.Attribute("aff4:rdfview",
                          RDFValueCollectionView,
                          "The list of attributes which will show up in "
                          "the table.",
                          default="")

  def Initialize(self):
    self.stream_dirty = False

  @property
  def fd(self):
    if self._fd is None:
      self._CreateStream()
    return self._fd

  @property
  def size(self):
    if self._fd is None:
      self._CreateStream()
    return self._size

  @size.setter
  def size(self, value):
    self._size = value

  def _CreateStream(self):
    """Lazily initializes the internal storage stream."""

    if "r" in self.mode:
      # We still have many collections which were created with a
      # versioned stream, which wastes space. Check if this is such a
      # collection and revert to the old behavior if necessary.
      urns = [self.urn.Add("UnversionedStream"), self.urn.Add("Stream")]

      for stream in aff4.FACTORY.MultiOpen(urns,
                                           mode=self.mode,
                                           token=self.token):
        if isinstance(stream, (aff4.AFF4UnversionedImage, aff4.AFF4Image)):
          self._fd = stream
          self._size = int(self.Get(self.Schema.SIZE))
          return

    # If we get here, we have to create a new stream.
    self._fd = aff4.FACTORY.Create(
        self.urn.Add("UnversionedStream"),
        aff4.AFF4UnversionedImage,
        mode=self.mode,
        token=self.token)
    self._fd.seek(0, 2)
    self._size = 0

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
    if self.locked:
      sync = True

    self.Flush(sync=sync)
    super(RDFValueCollection, self).Close(sync=sync)

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

    data = rdf_protodict.EmbeddedRDFValue(payload=rdf_value).SerializeToString()
    self.fd.Seek(0, 2)
    self.fd.Write(struct.pack("<i", len(data)))
    self.fd.Write(data)
    self.stream_dirty = True

    self.size += 1

  def AddAsMessage(self, rdfvalue_in, source):
    """Helper method to add rdfvalues as GrrMessages for testing."""
    self.Add(rdf_flows.GrrMessage(payload=rdfvalue_in, source=source))

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
      data = rdf_protodict.EmbeddedRDFValue(
          payload=rdf_value).SerializeToString()
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
  def deprecated_current_offset(self):
    return self.fd.Tell()

  def _GenerateItems(self, byte_offset=0):
    """Generates items starting from a given byte offset."""
    if not self.fd:
      return

    if self.mode == "w":
      raise RuntimeError("Can not read when in write mode.")

    self.fd.seek(byte_offset)
    count = 0

    while True:
      offset = self.fd.Tell()
      try:
        length = struct.unpack("<i", self.fd.Read(4))[0]
        serialized_event = self.fd.Read(length)
      except struct.error:
        break

      result = rdf_protodict.EmbeddedRDFValue(serialized_event)

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

  def GenerateItems(self, offset=0):
    """Iterate over all contained RDFValues.

    Args:
      offset: The offset in the stream to start reading from.

    Returns:
      Generator for values stored in the collection.

    Raises:
      RuntimeError: if we are in write mode.
    """
    return itertools.islice(self._GenerateItems(), offset, self.size)

  def GetItem(self, offset=0):
    for item in self.GenerateItems(offset=offset):
      return item

  def __getitem__(self, index):
    if index >= 0:
      for item in self.GenerateItems(offset=index):
        return item
    else:
      raise RuntimeError("Index must be >= 0")


class AFF4Collection(aff4.AFF4Volume, RDFValueCollection):
  """A collection of AFF4 objects.

  The AFF4 objects themselves are opened on demand from the data store. The
  collection simply stores the RDFURNs of all aff4 objects in the collection.
  """

  _rdf_type = rdf_client.AFF4ObjectSummary

  _behaviours = frozenset(["Collection"])

  class SchemaCls(aff4.AFF4Volume.SchemaCls, RDFValueCollection.SchemaCls):
    VIEW = aff4.Attribute("aff4:view",
                          AFF4CollectionView,
                          "The list of attributes which will show up in "
                          "the table.",
                          default="")

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
  _rdf_type = rdf_crypto.SignedBlob


class GRRSignedBlob(aff4.AFF4Stream):
  """A container for storing a signed binary blob such as a driver."""

  collection = None

  @classmethod
  def NewFromContent(cls,
                     content,
                     urn,
                     chunk_size=1024,
                     token=None,
                     private_key=None,
                     public_key=None,
                     prompt=True):
    """Alternate constructor for GRRSignedBlob.

    Creates a GRRSignedBlob from a content string by chunking it and signing
    each chunk.

    Args:
      content: The data to stored in the GRRSignedBlob.
      urn: The AFF4 URN to create.

      chunk_size: Data will be chunked into this size (each chunk is
        individually signed.
      token: The ACL Token.
      private_key: An rdf_crypto.PEMPrivateKey() instance.
      public_key: An rdf_crypto.PEMPublicKey() instance.
      prompt: If True we may present a prompt to unlock the key.

    Returns:
      the URN of the new object written.
    """
    with aff4.FACTORY.Create(urn, cls, mode="w", token=token) as fd:
      for start_of_chunk in xrange(0, len(content), chunk_size):
        chunk = content[start_of_chunk:start_of_chunk + chunk_size]
        blob_rdf = rdf_crypto.SignedBlob()
        blob_rdf.Sign(chunk, private_key, public_key, prompt=prompt)
        fd.Add(blob_rdf)

    return urn

  @property
  def size(self):
    self._EnsureInitialized()
    return self._size

  @size.setter
  def size(self, value):
    self._size = value

  @property
  def chunks(self):
    """Returns the total number of chunks."""
    self._EnsureInitialized()
    return len(self.collection)

  def _EnsureInitialized(self):
    if self.collection is None:
      if self.mode == "r":
        self.collection = aff4.FACTORY.Open(
            self.urn.Add("collection"),
            mode="r", token=self.token)
        self.fd = cStringIO.StringIO()
        for x in self.collection:
          self.fd.write(x.data)

        self._size = self.fd.tell()
        self.fd.seek(0)

      elif self.mode == "w":
        self.fd = cStringIO.StringIO()
        self._size = 0

        # Blind write.
        self.collection = aff4.FACTORY.Create(
            self.urn.Add("collection"),
            GRRSignedBlobCollection,
            mode="w",
            token=self.token)

      else:
        raise RuntimeError(
            "GRRSignedBlob can not be opened in mixed (rw) mode.")

  def Write(self, length):
    raise IOError("GRRSignedBlob is not writable. Please use "
                  "NewFromContent() to create a new GRRSignedBlob.")

  def Read(self, length):
    if self.mode != "r":
      raise IOError("Reading GRRSignedBlob opened for writing.")

    self._EnsureInitialized()
    return self.fd.read(length)

  def Add(self, item):
    if "r" in self.mode:
      raise IOError("GRRSignedBlob does not support appending.")
    self._EnsureInitialized()
    self.collection.Add(item)

  def __iter__(self):
    self._EnsureInitialized()
    return iter(self.collection)

  def Close(self):
    super(GRRSignedBlob, self).Close()
    if self.collection is not None:
      self.collection.Close()

  def __len__(self):
    return self.size

  def Tell(self):
    self._EnsureInitialized()
    return self.fd.tell()

  def Seek(self, offset, whence=0):
    self._EnsureInitialized()
    self.fd.seek(offset, whence)


class GrepResultsCollection(RDFValueCollection):
  """A collection of grep results."""
  _rdf_type = rdf_client.BufferReference


class ClientAnomalyCollection(RDFValueCollection):
  """A collection of anomalies related to a client.

  This class is a normal collection, but with additional methods for making
  viewing and working with anomalies easier.
  """
  _rdf_type = rdf_anomaly.Anomaly


class SeekIndexPair(rdf_structs.RDFProtoStruct):
  """Index offset <-> byte offset pair used in seek index."""

  protobuf = jobs_pb2.SeekIndexPair


class SeekIndex(rdf_structs.RDFProtoStruct):
  """Seek index (collection of SeekIndexPairs, essentially)."""

  protobuf = jobs_pb2.SeekIndex


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

  notification_queue = "aff4:/cron/versioned_collection_compactor"
  index_prefix = "index:changed/"
  index_format = index_prefix + "%s"

  @classmethod
  def ScheduleNotification(cls, urn, sync=False, token=None):
    """Schedule notification for a given urn."""
    data_store.DB.Set(cls.notification_queue,
                      cls.index_format % urn,
                      urn,
                      replace=True,
                      token=token,
                      sync=sync)

  @classmethod
  def QueryNotifications(cls, timestamp=None, token=None):
    """Query all the notifications for the given type of collections."""

    if token is None:
      raise ValueError("token can't be None")

    if timestamp is None:
      timestamp = rdfvalue.RDFDatetime().Now()

    for _, urn, urn_timestamp in data_store.DB.ResolvePrefix(
        cls.notification_queue,
        cls.index_prefix,
        timestamp=(0, timestamp),
        token=token):
      yield rdfvalue.RDFURN(urn, age=urn_timestamp)

  @classmethod
  def DeleteNotifications(cls, urns, end=None, token=None):
    """Delete notifications for given urns."""

    if token is None:
      raise ValueError("token can't be None")

    predicates = [cls.index_format % urn for urn in urns]
    data_store.DB.DeleteAttributes(cls.notification_queue,
                                   predicates,
                                   end=end,
                                   token=token,
                                   sync=True)

  @classmethod
  def AddToCollection(cls, collection_urn, rdf_values, sync=True, token=None):
    """Adds RDFValues to the collection with a given urn."""
    if token is None:
      raise ValueError("Token can't be None.")

    data_attrs = []
    for rdf_value in rdf_values:
      if rdf_value is None:
        raise ValueError("Can't add None to the collection.")

      if cls._rdf_type and not isinstance(rdf_value, cls._rdf_type):
        raise ValueError("This collection only accepts values of type %s" %
                         cls._rdf_type.__name__)

      if not rdf_value.age:
        rdf_value.age.Now()

      data_attrs.append(cls.SchemaCls.DATA(rdf_protodict.EmbeddedRDFValue(
          payload=rdf_value)))

    attrs_to_set = {cls.SchemaCls.DATA: data_attrs}
    if cls.IsJournalingEnabled():
      journal_entry = cls.SchemaCls.ADDITION_JOURNAL(len(rdf_values))
      attrs_to_set[cls.SchemaCls.ADDITION_JOURNAL] = [journal_entry]

    aff4.FACTORY.SetAttributes(collection_urn,
                               attrs_to_set,
                               set(),
                               add_child_index=False,
                               sync=sync,
                               token=token)
    cls.ScheduleNotification(collection_urn, token=token)

    # Update system-wide stats.
    stats.STATS.IncrementCounter("packed_collection_added",
                                 delta=len(rdf_values))

  class SchemaCls(RDFValueCollection.SchemaCls):
    """Schema for PackedVersionedCollection."""

    DATA = aff4.Attribute("aff4:data",
                          rdf_protodict.EmbeddedRDFValue,
                          "The embedded semantic value.",
                          versioned=True)

    SEEK_INDEX = aff4.Attribute("aff4:seek_index",
                                SeekIndex,
                                "Index for seek operations.",
                                versioned=False)

    ADDITION_JOURNAL = aff4.Attribute("aff4:addition_journal",
                                      rdfvalue.RDFInteger,
                                      "Journal of Add(), AddAll(), and "
                                      "AddToCollection() operations. Every "
                                      "element in the journal is the number of "
                                      "items added to collection when Add*() "
                                      "was called.",
                                      versioned=True)

    COMPACTION_JOURNAL = aff4.Attribute("aff4:compaction_journal",
                                        rdfvalue.RDFInteger,
                                        "Journal of compactions. Every item in "
                                        "the journal is number of elements "
                                        "that were compacted during particular "
                                        "compaction.")

  INDEX_INTERVAL = 10000
  COMPACTION_BATCH_SIZE = 10000
  MAX_REVERSED_RESULTS = 10000

  @staticmethod
  def IsJournalingEnabled():
    return config_lib.CONFIG[
        "Worker.enable_packed_versioned_collection_journaling"]

  def Flush(self, sync=True):
    send_notification = self._dirty and self.Schema.DATA in self.new_attributes
    super(PackedVersionedCollection, self).Flush(sync=sync)
    if send_notification:
      self.ScheduleNotification(self.urn, token=self.token)

  def Close(self, sync=True):
    send_notification = self._dirty and self.Schema.DATA in self.new_attributes
    super(PackedVersionedCollection, self).Close(sync=sync)
    if send_notification:
      self.ScheduleNotification(self.urn, token=self.token)

  def Add(self, rdf_value=None, **kwargs):
    """Add the rdf value to the collection."""
    if rdf_value is None and self._rdf_type:
      rdf_value = self._rdf_type(**kwargs)  # pylint: disable=not-callable

    if not rdf_value.age:
      rdf_value.age.Now()

    self.Set(self.Schema.DATA(payload=rdf_value))

    if self.IsJournalingEnabled():
      self.Set(self.Schema.ADDITION_JOURNAL(1))

    # Update system-wide stats.
    stats.STATS.IncrementCounter("packed_collection_added")

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

    if self.IsJournalingEnabled():
      self.Set(self.Schema.ADDITION_JOURNAL(len(rdf_values)))

    # Update system-wide stats.
    stats.STATS.IncrementCounter("packed_collection_added",
                                 delta=len(rdf_values))

  def GenerateUncompactedItems(self, max_reversed_results=0, timestamp=None):
    if self.IsAttributeSet(self.Schema.DATA):
      freeze_timestamp = timestamp or rdfvalue.RDFDatetime().Now()
      results = []
      for _, value, _ in data_store.DB.ResolvePrefix(
          self.urn,
          self.Schema.DATA.predicate,
          token=self.token,
          timestamp=(0, freeze_timestamp)):

        if results is not None:
          results.append(self.Schema.DATA(value).payload)
          if max_reversed_results and len(results) > max_reversed_results:
            for result in results:
              yield result
            results = None
        else:
          yield self.Schema.DATA(value).payload

      if results is not None:
        for result in reversed(results):
          yield result

  def GenerateItems(self, offset=0):
    """First iterate over the versions, and then iterate over the stream."""
    freeze_timestamp = rdfvalue.RDFDatetime().Now()

    index = 0
    byte_offset = 0
    if offset >= self.INDEX_INTERVAL and self.IsAttributeSet(
        self.Schema.SEEK_INDEX):
      seek_index = self.Get(self.Schema.SEEK_INDEX)
      for value in reversed(seek_index.checkpoints):
        if value.index_offset <= offset:
          index = value.index_offset
          byte_offset = value.byte_offset
          break

    for x in self._GenerateItems(byte_offset=byte_offset):
      if index >= offset:
        yield x
      index += 1

    for x in self.GenerateUncompactedItems(
        max_reversed_results=self.MAX_REVERSED_RESULTS,
        timestamp=freeze_timestamp):
      if index >= offset:
        yield x
      index += 1

  def GetIndex(self):
    """Return the seek index (in the reversed chronological order)."""
    if not self.IsAttributeSet(self.Schema.SEEK_INDEX):
      return []
    else:
      seek_index = self.Get(self.Schema.SEEK_INDEX)
      return [(v.index_offset, v.byte_offset)
              for v in reversed(seek_index.checkpoints)]

  @utils.Synchronized
  def Compact(self, callback=None, timestamp=None):
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
      timestamp: Only items added before this timestamp will be compacted.

    Raises:
      RuntimeError: if problems are encountered when reading back temporary
                    saved data.

    Returns:
      Number of compacted results.
    """
    if not self.locked:
      raise aff4.LockError("Collection must be locked before compaction.")

    compacted_count = 0

    batches_urns = []
    current_batch = []

    # This timestamp will be used to delete attributes. We don't want
    # to delete anything that was added after we started the compaction.
    freeze_timestamp = timestamp or rdfvalue.RDFDatetime().Now()

    def UpdateIndex():
      seek_index = self.Get(self.Schema.SEEK_INDEX, SeekIndex())

      prev_index_pair = seek_index.checkpoints and seek_index.checkpoints[-1]
      if (not prev_index_pair or
          self.size - prev_index_pair.index_offset >= self.INDEX_INTERVAL):
        new_index_pair = SeekIndexPair(index_offset=self.size,
                                       byte_offset=self.fd.Tell())
        seek_index.checkpoints.Append(new_index_pair)
        self.Set(self.Schema.SEEK_INDEX, seek_index)

    def DeleteVersionedDataAndFlush():
      """Removes versioned attributes and flushes the stream."""
      data_store.DB.DeleteAttributes(self.urn, [self.Schema.DATA.predicate],
                                     end=freeze_timestamp,
                                     token=self.token,
                                     sync=True)
      if self.IsJournalingEnabled():
        journal_entry = self.Schema.COMPACTION_JOURNAL(compacted_count,
                                                       age=freeze_timestamp)
        attrs_to_set = {self.Schema.COMPACTION_JOURNAL: [journal_entry]}
        aff4.FACTORY.SetAttributes(self.urn,
                                   attrs_to_set,
                                   set(),
                                   add_child_index=False,
                                   sync=True,
                                   token=self.token)

      if self.Schema.DATA in self.synced_attributes:
        del self.synced_attributes[self.Schema.DATA]

      self.Flush(sync=True)

    def HeartBeat():
      """Update the lock lease if needed and call the callback."""
      lease_time = config_lib.CONFIG["Worker.compaction_lease_time"]
      if self.CheckLease() < lease_time / 2:
        logging.info("%s: Extending compaction lease.", self.urn)
        self.UpdateLease(lease_time)
        stats.STATS.IncrementCounter("packed_collection_lease_extended")

      if callback:
        callback()

    HeartBeat()

    # We iterate over all versioned attributes. If we get more than
    # self.COMPACTION_BATCH_SIZE, we write the data to temporary
    # stream in the reversed order.
    for _, value, _ in data_store.DB.ResolvePrefix(
        self.urn,
        self.Schema.DATA.predicate,
        token=self.token,
        timestamp=(0, freeze_timestamp)):

      HeartBeat()

      current_batch.append(value)
      compacted_count += 1

      if len(current_batch) >= self.COMPACTION_BATCH_SIZE:
        batch_urn = rdfvalue.RDFURN("aff4:/tmp").Add("%X" %
                                                     utils.PRNG.GetULong())
        batches_urns.append(batch_urn)

        buf = cStringIO.StringIO()
        for data in reversed(current_batch):
          buf.write(struct.pack("<i", len(data)))
          buf.write(data)

        # We use AFF4Image to avoid serializing/deserializing data stored
        # in versioned attributes.
        with aff4.FACTORY.Create(batch_urn,
                                 aff4.AFF4Image,
                                 mode="w",
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
      self.size += len(current_batch)
      UpdateIndex()

      # If current_batch was the only available batch, just write everything
      # and return.
      if not batches_urns:
        DeleteVersionedDataAndFlush()
        return compacted_count

    batches = {}
    for batch in aff4.FACTORY.MultiOpen(batches_urns,
                                        aff4_type=aff4.AFF4Image,
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

      HeartBeat()

      data = batch.Read(len(batch))
      self.fd.Write(data)
      self.stream_dirty = True
      self.size += self.COMPACTION_BATCH_SIZE
      UpdateIndex()

      aff4.FACTORY.Delete(batch_urn, token=self.token)

    DeleteVersionedDataAndFlush()

    # Update system-wide stats.
    stats.STATS.IncrementCounter("packed_collection_compacted",
                                 delta=compacted_count)

    return compacted_count

  def CalculateLength(self):
    length = super(PackedVersionedCollection, self).__len__()

    if self.IsAttributeSet(self.Schema.DATA):
      if self.age_policy == aff4.ALL_TIMES:
        length += len(list(self.GetValuesForAttribute(self.Schema.DATA)))
      else:
        length += len(list(data_store.DB.ResolveMulti(
            self.urn, [self.Schema.DATA.predicate],
            token=self.token,
            timestamp=data_store.DB.ALL_TIMESTAMPS)))

    return length

  def __len__(self):
    return self.CalculateLength()

  def __nonzero__(self):
    if "r" not in self.mode:
      raise AttributeError(
          "Cannot determine collection length in write only mode.")

    # This checks if there is data in the stream.
    if super(PackedVersionedCollection, self).__nonzero__():
      return True

    # if there is not, we might have some uncompacted data.
    return self.IsAttributeSet(self.Schema.DATA)


# TODO(user): remove when we don't care about hunts with results
# in packed (and not sequential) collections.
class ResultsOutputCollection(PackedVersionedCollection):
  """Collection for hunt results storage.

  This collection is essentially a PackedVersionedCollection with a
  separate notification queue. Therefore, all new results are written
  as versioned attributes.

  This class is kept for backwards compatibility only and will be
  removed soon.
  """

  notification_queue = "aff4:/_notifications/results_output"

  class SchemaCls(PackedVersionedCollection.SchemaCls):
    RESULTS_SOURCE = aff4.Attribute("aff4:results_source", rdfvalue.RDFURN,
                                    "URN of a hunt where results came from.")

  @property
  def fd(self):
    if self._fd is None:
      self._CreateStream()
      if "w" in self.mode and self._fd.size == 0:
        # We want bigger chunks as we usually expect large number of results.
        self._fd.SetChunksize(1024 * 1024)

    return self._fd


class CollectionsInitHook(registry.InitHook):

  def RunOnce(self):
    """Register collections-related metrics."""
    stats.STATS.RegisterCounterMetric("packed_collection_added")
    stats.STATS.RegisterCounterMetric("packed_collection_compacted")
    stats.STATS.RegisterCounterMetric("packed_collection_lease_extended")
