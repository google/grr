#!/usr/bin/env python
"""These are standard aff4 objects."""


import StringIO

from grr.lib import aff4
from grr.lib import data_store
from grr.lib import flow
from grr.lib import rdfvalue
from grr.lib import utils
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import paths as rdf_paths


class Error(Exception):
  pass


class MissingBlobsError(aff4.MissingChunksError):
  pass


class VFSDirectory(aff4.AFF4Volume):
  """This represents a directory from the client."""
  default_container = "VFSDirectory"

  # We contain other objects within the tree.
  _behaviours = frozenset(["Container"])

  def Update(self, attribute=None, priority=None):
    """Refresh an old attribute.

    Note that refreshing the attribute is asynchronous. It does not change
    anything about the current object - you need to reopen the same URN some
    time later to get fresh data.

    Attributes:
       CONTAINS - Refresh the content of the directory listing.

    Args:
       attribute: An attribute object as listed above.
       priority: Priority to set for updating flow, None for default.

    Returns:
       The Flow ID that is pending

    Raises:
       IOError: If there has been an error starting the flow.
    """
    # client id is the first path element
    client_id = self.urn.Split()[0]

    if attribute == "CONTAINS":
      # Get the pathspec for this object
      flow_id = flow.GRRFlow.StartFlow(client_id=client_id,
                                       flow_name="ListDirectory",
                                       pathspec=self.real_pathspec,
                                       priority=priority,
                                       notify_to_user=False,
                                       token=self.token)

      return flow_id

  class SchemaCls(aff4.AFF4Volume.SchemaCls):
    """Attributes specific to VFSDirectory."""
    STAT = aff4.Attribute("aff4:stat", rdf_client.StatEntry,
                          "A StatEntry describing this file.", "stat")

    PATHSPEC = aff4.Attribute(
        "aff4:pathspec", rdf_paths.PathSpec,
        "The pathspec used to retrieve this object from the client.",
        "pathspec")


class HashList(rdfvalue.RDFBytes):
  """A list of hashes."""

  HASH_SIZE = 32

  def __len__(self):
    return len(self._value) / self.HASH_SIZE

  def __iter__(self):
    for i in range(len(self)):
      yield self[i]

  def __getitem__(self, idx):
    return rdfvalue.HashDigest(self._value[idx * self.HASH_SIZE:(idx + 1) *
                                           self.HASH_SIZE])


class BlobImage(aff4.AFF4ImageBase):
  """An AFF4 stream which stores chunks by hashes.

  The hash stream is kept within an AFF4 Attribute, instead of another stream
  making it more efficient for smaller files.
  """
  # Size of a sha256 hash
  _HASH_SIZE = 32

  # How many chunks we read ahead
  _READAHEAD = 5

  @classmethod
  def _GenerateChunkIds(cls, fds):
    for fd in fds:
      fd.index.seek(0)
      while True:
        chunk_id = fd.index.read(cls._HASH_SIZE)
        if not chunk_id:
          break
        yield chunk_id.encode("hex"), fd

  MULTI_STREAM_CHUNKS_READ_AHEAD = 1000

  @classmethod
  def _MultiStream(cls, fds):
    """Effectively streams data from multiple opened BlobImage objects.

    Args:
      fds: A list of opened AFF4Stream (or AFF4Stream descendants) objects.

    Yields:
      Tuples (chunk, fd, exception) where chunk is a binary blob of data and fd
      is an object from the fds argument.

      If one or more chunks are missing, exception is a MissingBlobsError object
      and chunk is None. _MultiStream does its best to skip the file entirely if
      one of its chunks is missing, but in case of very large files it's still
      possible to yield a truncated file.
    """

    broken_fds = set()
    missing_blobs_fd_pairs = []
    for chunk_fd_pairs in utils.Grouper(
        cls._GenerateChunkIds(fds), cls.MULTI_STREAM_CHUNKS_READ_AHEAD):
      results_map = data_store.DB.ReadBlobs(
          dict(chunk_fd_pairs).keys(),
          token=fds[0].token)

      for chunk_id, fd in chunk_fd_pairs:
        if chunk_id not in results_map or results_map[chunk_id] is None:
          missing_blobs_fd_pairs.append((chunk_id, fd))
          broken_fds.add(fd)

      for chunk, fd in chunk_fd_pairs:
        if fd in broken_fds:
          continue

        yield fd, results_map[chunk], None

    if missing_blobs_fd_pairs:
      missing_blobs_by_fd = {}
      for chunk_id, fd in missing_blobs_fd_pairs:
        missing_blobs_by_fd.setdefault(fd, []).append(chunk_id)

      for fd, missing_blobs in missing_blobs_by_fd.iteritems():
        e = MissingBlobsError("%d missing blobs (multi-stream)" %
                              len(missing_blobs),
                              missing_chunks=missing_blobs)
        yield fd, None, e

  def Initialize(self):
    super(BlobImage, self).Initialize()
    self.content_dirty = False
    if self.mode == "w":
      self.index = StringIO.StringIO("")
      self.finalized = False
    else:
      self.index = StringIO.StringIO(self.Get(self.Schema.HASHES, ""))
      self.finalized = self.Get(self.Schema.FINALIZED, False)

  def Truncate(self, offset=0):
    if offset != 0:
      raise IOError("Non-zero truncation not supported for BlobImage")
    super(BlobImage, self).Truncate(0)
    self.index = StringIO.StringIO("")
    self.finalized = False

  def _GetChunkForWriting(self, chunk):
    """Chunks must be added using the AddBlob() method."""
    raise NotImplementedError("Direct writing of HashImage not allowed.")

  def _GetChunkForReading(self, chunk):
    """Retrieve the relevant blob from the AFF4 data store or cache."""
    offset = chunk * self._HASH_SIZE
    self.index.seek(offset)

    chunk_name = self.index.read(self._HASH_SIZE).encode("hex")

    try:
      return self.chunk_cache.Get(chunk_name)
    except KeyError:
      pass

    # We don't have this chunk already cached. The most common read
    # access pattern is contiguous reading so since we have to go to
    # the data store already, we read ahead to reduce round trips.
    self.index.seek(offset)
    readahead = []

    for _ in range(self._READAHEAD):
      name = self.index.read(self._HASH_SIZE).encode("hex")
      if name and name not in self.chunk_cache:
        readahead.append(name)

    self._ReadChunks(readahead)
    try:
      return self.chunk_cache.Get(chunk_name)
    except KeyError:
      raise aff4.ChunkNotFoundError("Cannot open chunk %s" % chunk)

  def _ReadChunks(self, chunks):
    res = data_store.DB.ReadBlobs(chunks, token=self.token)
    for blob_hash, content in res.iteritems():
      fd = StringIO.StringIO(content)
      fd.dirty = False
      fd.chunk = blob_hash
      self.chunk_cache.Put(blob_hash, fd)

  def _WriteChunk(self, chunk):
    if chunk.dirty:
      data_store.DB.StoreBlob(chunk.getvalue(), token=self.token)

  def FromBlobImage(self, fd):
    """Copy this file cheaply from another BlobImage."""
    self.content_dirty = True
    self.SetChunksize(fd.chunksize)
    self.index = StringIO.StringIO(fd.index.getvalue())
    self.size = fd.size

  def Flush(self, sync=True):
    if self.content_dirty:
      self.Set(self.Schema.SIZE(self.size))
      self.Set(self.Schema.HASHES(self.index.getvalue()))
      self.Set(self.Schema.FINALIZED(self.finalized))
    super(BlobImage, self).Flush(sync)

  def AppendContent(self, src_fd):
    """Create new blob hashes and append to BlobImage.

    We don't support writing at arbitrary file offsets, but this method provides
    a convenient way to add blobs for a new file, or append content to an
    existing one.

    Args:
      src_fd: source file handle open for read
    Raises:
      IOError: if blob has already been finalized.
    """
    while 1:
      blob = src_fd.read(self.chunksize)
      if not blob:
        break

      blob_hash = data_store.DB.StoreBlob(blob, token=self.token)
      self.AddBlob(blob_hash.decode("hex"), len(blob))

    self.Flush()

  def AddBlob(self, blob_hash, length):
    """Add another blob to this image using its hash.

    Once a blob is added that is smaller than the chunksize we finalize the
    file, since handling adding more blobs makes the code much more complex.

    Args:
      blob_hash: sha256 binary digest
      length: int length of blob
    Raises:
      IOError: if blob has been finalized.
    """
    if self.finalized and length > 0:
      raise IOError("Can't add blobs to finalized BlobImage")

    self.content_dirty = True
    self.index.seek(0, 2)
    self.index.write(blob_hash)
    self.size += length

    if length < self.chunksize:
      self.finalized = True

  class SchemaCls(aff4.AFF4Image.SchemaCls):
    """The schema for Blob Images."""
    STAT = aff4.AFF4Object.VFSDirectory.SchemaCls.STAT

    HASHES = aff4.Attribute("aff4:hashes", HashList,
                            "List of hashes of each chunk in this file.")

    FINALIZED = aff4.Attribute("aff4:finalized", rdfvalue.RDFBool,
                               "Once a blobimage is finalized, further writes"
                               " will raise exceptions.")


class HashImage(aff4.AFF4Image):
  """An AFF4 Image which refers to chunks by their hash.

  This object stores a large image in chunks. Each chunk is stored using its
  hash in the AFF4 data store. We have an index with a series of hashes stored
  back to back. When we need to read a chunk, we seek the index for the hash,
  and then open the data blob indexed by this hash. Chunks are cached as per the
  AFF4Image implementation.

  Assumptions:
    Hashes do not collide.
    All data blobs have the same size (the chunk size), except possibly the last
    one in the file.
  """

  # Size of a sha256 hash
  _HASH_SIZE = 32

  # How many chunks we read ahead
  _READAHEAD = 5
  _data_dirty = False

  def Initialize(self):
    super(HashImage, self).Initialize()
    self.index = None

  def _OpenIndex(self):
    if self.index is None:
      index_urn = self.urn.Add("index")
      self.index = aff4.FACTORY.Create(index_urn,
                                       aff4.AFF4Image,
                                       mode=self.mode,
                                       token=self.token)

  def _GetChunkForWriting(self, chunk):
    """Chunks must be added using the AddBlob() method."""
    raise NotImplementedError("Direct writing of HashImage not allowed.")

  def _GetChunkForReading(self, chunk):
    """Retrieve the relevant blob from the AFF4 data store or cache."""
    self._OpenIndex()
    self.index.Seek(chunk * self._HASH_SIZE)

    chunk_name = self.index.Read(self._HASH_SIZE)
    try:
      return self.chunk_cache.Get(chunk_name)
    except KeyError:
      pass

    # Read ahead a few chunks.
    self.index.Seek(-self._HASH_SIZE, whence=1)
    readahead = []

    for _ in range(self._READAHEAD):
      name = self.index.Read(self._HASH_SIZE)
      if name and name not in self.chunk_cache:
        readahead.append(name.encode("hex"))

    res = data_store.DB.ReadBlobs(readahead, token=self.token)
    for blob_hash, content in res.iteritems():
      fd = StringIO.StringIO(content)
      fd.dirty = False
      fd.chunk = blob_hash
      self.chunk_cache.Put(blob_hash.decode("hex"), fd)

    return self.chunk_cache.Get(chunk_name)

  def Close(self, sync=True):
    if self._data_dirty:
      self.Set(self.Schema.SIZE(self.size))

    if self.index:
      self.index.Close(sync)

    super(HashImage, self).Close(sync)

  def AddBlob(self, blob_hash, length):
    """Add another blob to this image using its hash."""
    self._OpenIndex()
    self._data_dirty = True
    self.index.Seek(0, 2)
    self.index.Write(blob_hash)
    self.size += length

  class SchemaCls(aff4.AFF4Image.SchemaCls):
    """The schema for AFF4 files in the GRR VFS."""
    STAT = aff4.AFF4Object.VFSDirectory.SchemaCls.STAT


class AFF4SparseImage(aff4.AFF4ImageBase):
  """A class to store partial files."""

  _HASH_SIZE = 32

  _READAHEAD = 10

  chunksize = 512 * 1024

  class SchemaCls(aff4.AFF4ImageBase.SchemaCls):

    PATHSPEC = VFSDirectory.SchemaCls.PATHSPEC

    STAT = aff4.AFF4Object.VFSDirectory.SchemaCls.STAT

    _CHUNKSIZE = aff4.Attribute("aff4:chunksize",
                                rdfvalue.RDFInteger,
                                "Total size of each chunk.",
                                default=512 * 1024)

    LAST_CHUNK = aff4.Attribute("aff4:lastchunk",
                                rdfvalue.RDFInteger,
                                "The highest numbered chunk in this object.",
                                default=-1)

  def _ReadChunks(self, chunks):
    chunk_hashes = self._ChunkNrsToHashes(chunks)
    chunk_nrs = {}
    for k, v in chunk_hashes.iteritems():
      chunk_nrs.setdefault(v, []).append(k)
    res = data_store.DB.ReadBlobs(chunk_hashes.values(), token=self.token)
    for blob_hash, content in res.iteritems():
      for chunk_nr in chunk_nrs[blob_hash]:
        fd = StringIO.StringIO(content)
        fd.dirty = False
        fd.chunk = chunk_nr
        self.chunk_cache.Put(chunk_nr, fd)

  def _WriteChunk(self, chunk):
    if chunk.dirty:
      data_store.DB.StoreBlob(chunk.getvalue(), token=self.token)

  def _ChunkNrToHash(self, chunk_nr):
    return self._ChunkNrsToHashes([chunk_nr])[chunk_nr]

  def _ChunkNrsToHashes(self, chunk_nrs):
    chunk_names = {self.urn.Add(self.CHUNK_ID_TEMPLATE % chunk_nr): chunk_nr
                   for chunk_nr in chunk_nrs}
    res = {}
    for obj in aff4.FACTORY.MultiOpen(chunk_names, mode="r", token=self.token):
      if isinstance(obj, aff4.AFF4Stream):
        hsh = obj.read(self._HASH_SIZE)
        if hsh:
          res[chunk_names[obj.urn]] = hsh.encode("hex")
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

    fd = StringIO.StringIO()
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
    chunk = self.offset / self.chunksize
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

    return "".join(result)

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
    if len(blob_hash) != self._HASH_SIZE:
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
    with aff4.FACTORY.Create(index_urn,
                             aff4.AFF4MemoryStream,
                             token=self.token) as fd:
      fd.write(blob_hash)
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

    for metadata in aff4.FACTORY.Stat(index_urns, token=self.token):
      res[index_urns[metadata["urn"]]] = True

    return res

  def ChunksMetadata(self, chunk_numbers):
    index_urns = {
        self.urn.Add(self.CHUNK_ID_TEMPLATE % chunk_number): chunk_number
        for chunk_number in chunk_numbers
    }

    res = {}

    for metadata in aff4.FACTORY.Stat(index_urns, token=self.token):
      res[index_urns[metadata["urn"]]] = metadata

    return res

  def Flush(self, sync=True):
    if self._dirty:
      self.Set(self.Schema.LAST_CHUNK, rdfvalue.RDFInteger(self.last_chunk))
    super(AFF4SparseImage, self).Flush(sync=sync)


class LabelSet(aff4.AFF4Object):
  """An aff4 object which manages a set of labels.

  This object has no actual attributes, it simply manages the set.
  """

  # We expect the set to be quite small, so we simply store it as a collection
  # attributes of the form "index:label_<label>" all unversioned (ts = 0).

  PLACEHOLDER_VALUE = "X"

  ATTRIBUTE_PREFIX = "index:label_"
  ATTRIBUTE_PATTERN = "index:label_%s"

  # Location of the default set of labels, used to keep tract of active labels
  # for clients.
  CLIENT_LABELS_URN = "aff4:/index/labels/client_set"

  def __init__(self, urn, **kwargs):
    super(LabelSet, self).__init__(urn=self.CLIENT_LABELS_URN, **kwargs)

    self.to_set = set()
    self.to_delete = set()

  def Flush(self, sync=False):
    """Flush the data to the index."""
    super(LabelSet, self).Flush(sync=sync)

    self.to_delete = self.to_delete.difference(self.to_set)

    to_set = dict(zip(self.to_set, self.PLACEHOLDER_VALUE * len(self.to_set)))

    if to_set or self.to_delete:
      data_store.DB.MultiSet(self.urn,
                             to_set,
                             to_delete=list(self.to_delete),
                             timestamp=0,
                             token=self.token,
                             replace=True,
                             sync=sync)
    self.to_set = set()
    self.to_delete = set()

  def Close(self, sync=False):
    self.Flush(sync=sync)
    super(LabelSet, self).Close(sync=sync)

  def Add(self, label):
    self.to_set.add(self.ATTRIBUTE_PATTERN % label)

  def Remove(self, label):
    self.to_delete.add(self.ATTRIBUTE_PATTERN % label)

  def ListLabels(self):
    # Flush, so that any pending changes are visible.
    if self.to_set or self.to_delete:
      self.Flush(sync=True)
    result = []
    for attribute, _, _ in data_store.DB.ResolvePrefix(self.urn,
                                                       self.ATTRIBUTE_PREFIX,
                                                       token=self.token):
      result.append(attribute[len(self.ATTRIBUTE_PREFIX):])
    return sorted(result)


class TempMemoryFile(aff4.AFF4MemoryStream):
  """A temporary AFF4MemoryStream-based file with a random URN."""

  def __init__(self, urn, **kwargs):
    if urn is None:
      urn = rdfvalue.RDFURN("aff4:/tmp").Add("%X" % utils.PRNG.GetULong())

    super(TempMemoryFile, self).__init__(urn, **kwargs)


class TempImageFile(aff4.AFF4Image):
  """A temporary file AFF4Image-based file with a random URN."""

  def __init__(self, urn, **kwargs):
    if urn is None:
      urn = rdfvalue.RDFURN("aff4:/tmp").Add("%X" % utils.PRNG.GetULong())

    super(TempImageFile, self).__init__(urn, **kwargs)
