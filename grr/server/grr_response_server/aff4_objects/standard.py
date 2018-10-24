#!/usr/bin/env python
"""These are standard aff4 objects."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import io


from builtins import range  # pylint: disable=redefined-builtin
from future.utils import iteritems
from future.utils import itervalues

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_server import aff4
from grr_response_server import data_store
from grr_response_server import flow
from grr_response_server.rdfvalues import objects as rdf_objects


class VFSDirectory(aff4.AFF4Volume):
  """This represents a directory from the client."""

  # We contain other objects within the tree.
  _behaviours = frozenset(["Container"])

  def Update(self, attribute=None):
    """Refresh an old attribute.

    Note that refreshing the attribute is asynchronous. It does not change
    anything about the current object - you need to reopen the same URN some
    time later to get fresh data.

    Attributes: CONTAINS - Refresh the content of the directory listing.
    Args:
       attribute: An attribute object as listed above.

    Returns:
       The Flow ID that is pending

    Raises:
       IOError: If there has been an error starting the flow.
    """
    # client id is the first path element
    client_id = self.urn.Split()[0]

    if attribute == "CONTAINS":
      # Get the pathspec for this object
      flow_id = flow.StartAFF4Flow(
          client_id=client_id,
          # Dependency loop: aff4_objects/aff4_grr.py depends on
          # aff4_objects/standard.py that depends on flows/general/filesystem.py
          # that eventually depends on aff4_objects/aff4_grr.py
          # flow_name=filesystem.ListDirectory.__name__,
          flow_name="ListDirectory",
          pathspec=self.real_pathspec,
          notify_to_user=False,
          token=self.token)

      return flow_id

  class SchemaCls(aff4.AFF4Volume.SchemaCls):
    """Attributes specific to VFSDirectory."""
    STAT = aff4.Attribute("aff4:stat", rdf_client_fs.StatEntry,
                          "A StatEntry describing this file.", "stat")

    PATHSPEC = aff4.Attribute(
        "aff4:pathspec", rdf_paths.PathSpec,
        "The pathspec used to retrieve this object from the client.",
        "pathspec")


class HashList(rdfvalue.RDFBytes):
  """A list of hashes."""

  HASH_SIZE = 32

  def __len__(self):
    return len(self._value) // self.HASH_SIZE

  def __iter__(self):
    for i in range(len(self)):
      yield self[i]

  def __getitem__(self, idx):
    return rdfvalue.HashDigest(
        self._value[idx * self.HASH_SIZE:(idx + 1) * self.HASH_SIZE])


class AFF4SparseImage(aff4.AFF4ImageBase):
  """A class to store partial files."""

  _HASH_SIZE = 32

  _READAHEAD = 10

  chunksize = 512 * 1024

  class SchemaCls(aff4.AFF4ImageBase.SchemaCls):
    """The schema class for AFF4SparseImage."""

    PATHSPEC = VFSDirectory.SchemaCls.PATHSPEC

    STAT = VFSDirectory.SchemaCls.STAT

    _CHUNKSIZE = aff4.Attribute(
        "aff4:chunksize",
        rdfvalue.RDFInteger,
        "Total size of each chunk.",
        default=512 * 1024)

    LAST_CHUNK = aff4.Attribute(
        "aff4:lastchunk",
        rdfvalue.RDFInteger,
        "The highest numbered chunk in this object.",
        default=-1)

  def _ReadChunks(self, chunks):
    chunk_hashes = self._ChunkNrsToHashes(chunks)
    chunk_nrs = {}
    for k, v in iteritems(chunk_hashes):
      chunk_nrs.setdefault(v, []).append(k)

    res = data_store.BLOBS.ReadBlobs(list(itervalues(chunk_hashes)))
    for blob_hash, content in iteritems(res):
      for chunk_nr in chunk_nrs[blob_hash]:
        fd = io.BytesIO(content)
        fd.dirty = False
        fd.chunk = chunk_nr
        self.chunk_cache.Put(chunk_nr, fd)

  def _WriteChunk(self, chunk):
    if chunk.dirty:
      data_store.BLOBS.WriteBlobWithUnknownHash(chunk.getvalue())

  def _ChunkNrToHash(self, chunk_nr):
    return self._ChunkNrsToHashes([chunk_nr])[chunk_nr]

  def _ChunkNrsToHashes(self, chunk_nrs):
    chunk_names = {
        self.urn.Add(self.CHUNK_ID_TEMPLATE % chunk_nr): chunk_nr
        for chunk_nr in chunk_nrs
    }
    res = {}
    for obj in aff4.FACTORY.MultiOpen(chunk_names, mode="r", token=self.token):
      if isinstance(obj, aff4.AFF4Stream):
        hsh = obj.read(self._HASH_SIZE)
        if hsh:
          res[chunk_names[obj.urn]] = rdf_objects.BlobID.FromBytes(hsh)
    return res

  def _GetChunkForReading(self, chunk):
    """Returns the relevant chunk from the datastore and reads ahead."""
    try:
      return self.chunk_cache.Get(chunk)
    except KeyError:
      pass

    # We don't have this chunk already cached. The most common read
    # access pattern is contiguous reading so since we have to go to
    # the data store already, we read ahead to reduce round trips.

    missing_chunks = []
    for chunk_number in range(chunk, chunk + 10):
      if chunk_number not in self.chunk_cache:
        missing_chunks.append(chunk_number)

    self._ReadChunks(missing_chunks)
    # This should work now - otherwise we just give up.
    try:
      return self.chunk_cache.Get(chunk)
    except KeyError:
      raise aff4.ChunkNotFoundError("Cannot open chunk %s" % chunk)

  def _GetChunkForWriting(self, chunk):
    """Returns the relevant chunk from the datastore."""
    try:
      chunk = self.chunk_cache.Get(chunk)
      chunk.dirty = True
      return chunk
    except KeyError:
      pass

    try:
      chunk = self._ReadChunk(chunk)
      chunk.dirty = True
      return chunk
    except KeyError:
      pass

    fd = io.BytesIO()
    fd.chunk = chunk
    fd.dirty = True
    self.chunk_cache.Put(chunk, fd)

    # Keep track of the biggest chunk_number we've seen so far.
    if chunk > self.last_chunk:
      self.last_chunk = chunk
      self._dirty = True

    return fd

  def _ReadPartial(self, length):
    """Read as much as possible, but not more than length."""
    chunk = self.offset // self.chunksize
    chunk_offset = self.offset % self.chunksize

    # If we're past the end of the file, we don't have a chunk to read from, so
    # we can't read anymore. We return the empty string here so we can read off
    # the end of a file without raising, and get as much data as is there.
    if chunk > self.last_chunk:
      return ""

    available_to_read = min(length, self.chunksize - chunk_offset)

    fd = self._GetChunkForReading(chunk)

    fd.seek(chunk_offset)

    result = fd.read(available_to_read)
    self.offset += len(result)

    return result

  def Read(self, length):
    result = []

    # Make sure we don't read past the "end" of the file. We say the end is the
    # end of the last chunk. If we do try and read past the end, we should
    # return an empty string.
    # The end of the file is the *end* of the last chunk, so we add one here.
    length = min(length, ((self.last_chunk + 1) * self.chunksize) - self.offset)

    while length > 0:
      data = self._ReadPartial(length)
      if not data:
        break
      length -= len(data)
      result.append(data)

    return b"".join(result)

  def Initialize(self):
    super(AFF4SparseImage, self).Initialize()
    if "r" in self.mode:
      # pylint: disable=protected-access
      self.chunksize = int(self.Get(self.Schema._CHUNKSIZE))
      # pylint: enable=protected-access
      self.content_last = self.Get(self.Schema.CONTENT_LAST)
      # The chunk with the highest index we've seen so far. We'll use
      # this to keep track of what the biggest possible size this file
      # could be is.
      self.last_chunk = self.Get(self.Schema.LAST_CHUNK)
    else:
      self.size = 0
      self.content_last = None
      self.last_chunk = -1

  def Truncate(self, offset=0):
    if offset != 0:
      raise IOError("Non-zero truncation not supported for AFF4SparseImage")
    super(AFF4SparseImage, self).Truncate(0)

  def AddBlob(self, blob_hash, length, chunk_number):
    """Add another blob to this image using its hash."""
    if len(blob_hash.AsBytes()) != self._HASH_SIZE:
      raise ValueError("Hash '%s' doesn't have correct length (%d)." %
                       (blob_hash, self._HASH_SIZE))

    # If we're adding a new blob, we should increase the size. If we're just
    # updating an existing blob, the size should stay the same.
    # That is, if we read the index at the right offset and no hash is there, we
    # must not have seen this blob before, so we say we're adding a new one and
    # increase in size.
    if not self.ChunkExists(chunk_number):
      # We say that we've increased in size by the size of the blob,
      # but really we only store its hash in the AFF4SparseImage.
      self.size += length
      self._dirty = True
      # Keep track of the biggest chunk_number we've seen so far.
      if chunk_number > self.last_chunk:
        self.last_chunk = chunk_number
        self._dirty = True

    index_urn = self.urn.Add(self.CHUNK_ID_TEMPLATE % chunk_number)
    # TODO(amoser): This opens a subobject for each AddBlob call :/
    with aff4.FACTORY.Create(
        index_urn, aff4.AFF4MemoryStream, token=self.token) as fd:
      fd.write(blob_hash.AsBytes())
    if chunk_number in self.chunk_cache:
      self.chunk_cache.Pop(chunk_number)

  def ChunkExists(self, chunk_number):
    return self.ChunksExist([chunk_number])[chunk_number]

  def ChunksExist(self, chunk_numbers):
    """Do we have this chunk in the index?"""
    index_urns = {
        self.urn.Add(self.CHUNK_ID_TEMPLATE % chunk_number): chunk_number
        for chunk_number in chunk_numbers
    }

    res = {chunk_number: False for chunk_number in chunk_numbers}

    for metadata in aff4.FACTORY.Stat(index_urns):
      res[index_urns[metadata["urn"]]] = True

    return res

  def ChunksMetadata(self, chunk_numbers):
    index_urns = {
        self.urn.Add(self.CHUNK_ID_TEMPLATE % chunk_number): chunk_number
        for chunk_number in chunk_numbers
    }

    res = {}

    for metadata in aff4.FACTORY.Stat(index_urns):
      res[index_urns[metadata["urn"]]] = metadata

    return res

  def Flush(self):
    if self._dirty:
      self.Set(self.Schema.LAST_CHUNK, rdfvalue.RDFInteger(self.last_chunk))
    super(AFF4SparseImage, self).Flush()


class LabelSet(aff4.AFF4Object):
  """An aff4 object which manages a set of labels.

  This object has no actual attributes, it simply manages the set.
  """

  # We expect the set to be quite small, so we simply store it as a collection
  # attributes of the form "index:label_<label>" all unversioned (ts = 0).

  # Location of the default set of labels, used to keep tract of active labels
  # for clients.
  CLIENT_LABELS_URN = "aff4:/index/labels/client_set"

  def __init__(self, urn, **kwargs):
    super(LabelSet, self).__init__(urn=self.CLIENT_LABELS_URN, **kwargs)

    self.to_set = set()
    self.to_delete = set()

  def Flush(self):
    """Flush the data to the index."""
    super(LabelSet, self).Flush()

    self.to_delete = self.to_delete.difference(self.to_set)

    with data_store.DB.GetMutationPool() as mutation_pool:
      mutation_pool.LabelUpdateLabels(
          self.urn, self.to_set, to_delete=self.to_delete)
    self.to_set = set()
    self.to_delete = set()

  def Close(self):
    self.Flush()
    super(LabelSet, self).Close()

  def Add(self, label):
    self.to_set.add(label)

  def Remove(self, label):
    self.to_delete.add(label)

  def ListLabels(self):
    # Flush, so that any pending changes are visible.
    if self.to_set or self.to_delete:
      self.Flush()
    return data_store.DB.LabelFetchAll(self.urn)
