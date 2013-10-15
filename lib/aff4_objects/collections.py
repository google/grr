#!/usr/bin/env python
"""Implementations of various collections."""



import cStringIO
import struct

from grr.lib import aff4
from grr.lib import data_store
from grr.lib import rdfvalue
from grr.lib.aff4_objects import aff4_grr
from grr.lib.flows.cron import compactors


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
    if self._dirty and self.fd:
      self.fd.Flush(sync=sync)
      self.Set(self.Schema.SIZE(self.size))

    super(RDFValueCollection, self).Flush(sync=sync)

  def Close(self, sync=False):
    self.Flush(sync=sync)

  def Add(self, rdf_value=None, **kwargs):
    """Add the rdf value to the collection."""
    if rdf_value is None and self._rdf_type:
      rdf_value = self._rdf_type(**kwargs)  # pylint: disable=not-callable

    if self._rdf_type and not isinstance(rdf_value, self._rdf_type):
      raise RuntimeError("This collection only accepts values of type %s" %
                         self._rdf_type.__name__)

    if not rdf_value.age:
      rdf_value.age.Now()

    data = rdfvalue.EmbeddedRDFValue(payload=rdf_value).SerializeToString()
    self.fd.Seek(0, 2)
    self.fd.Write(struct.pack("<i", len(data)))
    self.fd.Write(data)
    self.size += 1
    self._dirty = True

  def AddAll(self, rdf_values):
    """Adds a list of rdfvalues to the collection."""
    for rdf_value in rdf_values:
      if self._rdf_type and not isinstance(rdf_value, self._rdf_type):
        raise RuntimeError("This collection only accepts values of type %s" %
                           self._rdf_type.__name__)

      if not rdf_value.age:
        rdf_value.age.Now()

    buf = cStringIO.StringIO()
    for rdf_value in rdf_values:
      data = rdfvalue.EmbeddedRDFValue(payload=rdf_value).SerializeToString()
      buf.write(struct.pack("<i", len(data)))
      buf.write(data)
    self.fd.Seek(0, 2)
    self.fd.Write(buf.getvalue())
    self.size += len(rdf_values)
    self._dirty = True

  def __len__(self):
    return self.size

  def __iter__(self):
    """Iterate over all contained RDFValues.

    Returns:
      Generator of RDFValues stored in the collection.

    Raises:
      RuntimeError: if we are in write mode.
    """
    return self.GenerateItems()

  def GenerateItems(self):
    """Iterate over all contained RDFValues.

    Yields:
      RDFValues stored in the collection.

    Raises:
      RuntimeError: if we are in write mode.
    """
    if not self.fd:
      return

    if self.mode == "w":
      raise RuntimeError("Can not read when in write mode.")

    self.fd.seek(0)
    while True:
      try:
        length = struct.unpack("<i", self.fd.Read(4))[0]
        serialized_event = self.fd.Read(length)
      except struct.error:
        break

      result = rdfvalue.EmbeddedRDFValue(serialized_event)
      yield result.payload

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


class GrepResultsCollection(RDFValueCollection):
  """A collection of grep results."""
  _rdf_type = rdfvalue.BufferReference


class VersionedCollection(RDFValueCollection):
  """A collection which uses the data store's version properties.

  This collection is very efficient for writing to - we can insert new values by
  blind writing them into the data store without needing to take a lock - using
  the timestamping features of the data store.
  """

  class SchemaCls(RDFValueCollection.SchemaCls):
    DATA = aff4.Attribute("aff4:data", rdfvalue.EmbeddedRDFValue,
                          "The embedded semantic value.", versioned=True)

  def Initialize(self):
    self.fd = None

  def Add(self, rdf_value=None, **kwargs):
    """Add the rdf value to the collection."""
    if rdf_value is None and self._rdf_type:
      rdf_value = self._rdf_type(**kwargs)  # pylint: disable-msg=not-callable

    if not rdf_value.age:
      rdf_value.age.Now()

    self.AddAttribute(self.Schema.DATA(payload=rdf_value,
                                       age=rdf_value.age), age=rdf_value.age)

  def GenerateItems(self, timestamp=None):
    if timestamp is None:
      timestamp = data_store.DB.ALL_TIMESTAMPS

    for _, value, ts in data_store.DB.ResolveMulti(
        self.urn, [self.Schema.DATA.predicate], token=self.token,
        timestamp=timestamp):
      yield self.Schema.DATA(value, age=ts).payload


class PackedVersionedCollection(RDFValueCollection):
  """A collection which uses the data store's version properties.

  This collection is very efficient for writing to - we can insert new values by
  blind writing them into the data store - using the timestamping features of
  the data store.

  Unfortunately reading from versioned data store attributes is slow. Therefore
  this object implements a compaction strategy, where writes are versioned,
  until they can be compacted into a regular RDFValueCollection by then
  VersionedCollectionCompactor cron job.
  """

  class SchemaCls(RDFValueCollection.SchemaCls):
    DATA = aff4.Attribute("aff4:data", rdfvalue.EmbeddedRDFValue,
                          "The embedded semantic value.", versioned=True)

  def Add(self, rdf_value=None, **kwargs):
    """Add the rdf value to the collection."""
    if rdf_value is None and self._rdf_type:
      rdf_value = self._rdf_type(**kwargs)  # pylint: disable-msg=not-callable

    if not rdf_value.age:
      rdf_value.age.Now()

    self.Set(self.Schema.DATA(payload=rdf_value, age=rdf_value.age))

    # Let the compactor know we need compacting.
    data_store.DB.Set(compactors.PackedVersionedCollectionCompactor.URN,
                      "index:changed/%s" % self.urn, self.urn,
                      replace=True, token=self.token, sync=False)

  def GenerateItems(self):
    # First iterate over the versions, and then iterate over the stream.
    for _, value, _ in data_store.DB.ResolveMulti(
        self.urn, [self.Schema.DATA.predicate], token=self.token,
        timestamp=data_store.DB.ALL_TIMESTAMPS):
      yield self.Schema.DATA(value).payload

    for x in super(
        PackedVersionedCollection, self).GenerateItems():
      yield x
