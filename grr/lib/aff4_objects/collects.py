#!/usr/bin/env python
"""Implementations of various collections."""



import cStringIO
import itertools
import struct

import logging

from grr.lib import aff4
from grr.lib import rdfvalue
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

    VIEW = aff4.Attribute(
        "aff4:rdfview",
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

      for stream in aff4.FACTORY.MultiOpen(
          urns, mode=self.mode, token=self.token):
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
      rdf_value.age = rdfvalue.RDFDatetime.Now()

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
        rdf_value.age = rdfvalue.RDFDatetime.Now()

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

      result = rdf_protodict.EmbeddedRDFValue.FromSerializedString(
          serialized_event)

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
                     public_key=None):
    """Alternate constructor for GRRSignedBlob.

    Creates a GRRSignedBlob from a content string by chunking it and signing
    each chunk.

    Args:
      content: The data to stored in the GRRSignedBlob.
      urn: The AFF4 URN to create.

      chunk_size: Data will be chunked into this size (each chunk is
        individually signed.
      token: The ACL Token.
      private_key: An rdf_crypto.RSAPrivateKey() instance.
      public_key: An rdf_crypto.RSAPublicKey() instance.

    Returns:
      the URN of the new object written.
    """
    with aff4.FACTORY.Create(urn, cls, mode="w", token=token) as fd:
      for start_of_chunk in xrange(0, len(content), chunk_size):
        chunk = content[start_of_chunk:start_of_chunk + chunk_size]
        blob_rdf = rdf_crypto.SignedBlob()
        blob_rdf.Sign(chunk, private_key, public_key)
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
        self.fd = cStringIO.StringIO()
        try:
          self.collection = aff4.FACTORY.Open(
              self.urn.Add("collection"),
              aff4_type=GRRSignedBlobCollection,
              mode="r",
              token=self.token)
        except aff4.InstantiationError:
          self._size = 0
          return

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
  rdf_deps = [
      SeekIndexPair,
  ]
