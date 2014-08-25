#!/usr/bin/env python
"""These are standard aff4 objects."""


import hashlib
import re
import StringIO

from grr.lib import aff4
from grr.lib import data_store
from grr.lib import flow
from grr.lib import rdfvalue
from grr.lib import utils


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

    if attribute == self.Schema.CONTAINS:
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
    STAT = aff4.Attribute("aff4:stat", rdfvalue.StatEntry,
                          "A StatResponse protobuf describing this file.",
                          "stat")

    PATHSPEC = aff4.Attribute(
        "aff4:pathspec", rdfvalue.PathSpec,
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
    return rdfvalue.HashDigest(
        self._value[idx * self.HASH_SIZE: (idx + 1) * self.HASH_SIZE])


class BlobImage(aff4.AFF4Image):
  """An AFF4 stream which stores chunks by hashes.

  The hash stream is kept within an AFF4 Attribute, instead of another stream
  making it more efficient for smaller files.
  """
  # Size of a sha256 hash
  _HASH_SIZE = 32

  # How many chunks we read ahead
  _READAHEAD = 5

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
    result = None
    offset = chunk * self._HASH_SIZE
    self.index.seek(offset)

    chunk_name = self.index.read(self._HASH_SIZE)
    try:
      result = self.chunk_cache.Get(chunk_name)
    except KeyError:
      # Read ahead a few chunks.
      self.index.seek(offset)
      readahead = {}

      for _ in range(self._READAHEAD):
        name = self.index.read(self._HASH_SIZE)
        if name and name not in self.chunk_cache:
          urn = aff4.ROOT_URN.Add("blobs").Add(name.encode("hex"))
          readahead[urn] = name

      fds = aff4.FACTORY.MultiOpen(readahead, mode="r", token=self.token)
      for fd in fds:
        name = readahead[fd.urn]

        # Remember the right fd
        if name == chunk_name:
          result = fd

        # Put back into the cache
        self.chunk_cache.Put(readahead[fd.urn], fd)

    if result is None:
      raise IOError("Chunk '%s' not found for reading!" % chunk)

    return result

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
      blob_hash = hashlib.sha256(blob).digest()
      blob_urn = rdfvalue.RDFURN("aff4:/blobs").Add(blob_hash.encode("hex"))

      try:
        fd = aff4.FACTORY.Open(blob_urn, "AFF4MemoryStream", mode="r",
                               token=self.token)
      except IOError:
        fd = aff4.FACTORY.Create(blob_urn, "AFF4MemoryStream", mode="w",
                                 token=self.token)
        fd.Write(blob)
        fd.Close(sync=True)

      self.AddBlob(blob_hash, len(blob))

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

    HASHES = aff4.Attribute("aff4:hashes", rdfvalue.HashList,
                            "List of hashes of each chunk in this file.")

    FINGERPRINT = aff4.Attribute("aff4:fingerprint",
                                 rdfvalue.FingerprintResponse,
                                 "DEPRECATED protodict containing arrays of "
                                 " hashes. Use AFF4Stream.HASH instead.")

    FINALIZED = aff4.Attribute("aff4:finalized",
                               rdfvalue.RDFBool,
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
      self.index = aff4.FACTORY.Create(index_urn, "AFF4Image", mode=self.mode,
                                       token=self.token)

  def _GetChunkForWriting(self, chunk):
    """Chunks must be added using the AddBlob() method."""
    raise NotImplementedError("Direct writing of HashImage not allowed.")

  def _GetChunkForReading(self, chunk):
    """Retrieve the relevant blob from the AFF4 data store or cache."""
    result = None
    self._OpenIndex()
    self.index.Seek(chunk * self._HASH_SIZE)

    chunk_name = self.index.Read(self._HASH_SIZE)
    try:
      result = self.chunk_cache.Get(chunk_name)
    except KeyError:
      # Read ahead a few chunks.
      self.index.Seek(-self._HASH_SIZE, whence=1)
      readahead = {}

      for _ in range(self._READAHEAD):
        name = self.index.Read(self._HASH_SIZE)
        if name and name not in self.chunk_cache:
          urn = aff4.ROOT_URN.Add("blobs").Add(name.encode("hex"))
          readahead[urn] = name

      fds = aff4.FACTORY.MultiOpen(readahead, mode="r", token=self.token)
      for fd in fds:
        name = readahead[fd.urn]

        # Remember the right fd
        if name == chunk_name:
          result = fd

        # Put back into the cache
        self.chunk_cache.Put(readahead[fd.urn], fd)

    return result

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
    CONTENT_LOCK = aff4.Attribute(
        "aff4:content_lock", rdfvalue.RDFURN,
        "This lock contains a URN pointing to the flow that is currently "
        "updating this object.")

    FINGERPRINT = aff4.Attribute("aff4:fingerprint",
                                 rdfvalue.FingerprintResponse,
                                 "DEPRECATED protodict containing arrays of "
                                 " hashes. Use AFF4Stream.HASH instead.")


class AFF4SparseImage(BlobImage):
  """A class to store partial files."""

  class SchemaCls(aff4.BlobImage.SchemaCls):
    PATHSPEC = VFSDirectory.SchemaCls.PATHSPEC

  def Initialize(self):
    super(AFF4SparseImage, self).Initialize()
    self._OpenIndex()

  def _OpenIndex(self):
    """Create the index if it doesn't exist, otherwise open it."""
    index_urn = self.urn.Add("index")
    self.index = aff4.FACTORY.Create(index_urn, "AFF4SparseIndex", mode="rw",
                                     token=self.token)

  def Truncate(self, offset=0):
    if offset != 0:
      raise IOError("Non-zero truncation not supported for AFF4SparseImage")
    super(AFF4SparseImage, self).Truncate(0)
    self._OpenIndex()
    self.finalized = False

  def Read(self, length):
    result = []

    while length > 0:
      data = self._ReadPartial(length)
      if not data:
        break
      length -= len(data)
      result.append(data)

    return "".join(result)

  def _GetChunkForReading(self, chunk):
    """Retrieve the relevant blob from the AFF4 data store or cache."""
    result = None
    offset = chunk * self._HASH_SIZE
    self.index.seek(offset)
    chunk_name = self.index.read(self._HASH_SIZE)
    try:
      result = self.chunk_cache.Get(chunk_name)
      # Cache hit, so we're done.
      return result
    except KeyError:
      # Read ahead a few chunks.
      self.index.seek(offset)
      readahead = {}

      # Read all the hashes in one go, then split up the result.
      chunks = self.index.read(self._HASH_SIZE * self._READAHEAD)
      chunk_names = [chunks[i:i + self._HASH_SIZE]
                     for i in xrange(0, len(chunks), self._HASH_SIZE)]

      for name in chunk_names:
        # Try and read ahead a few chunks from the datastore and add them to the
        # cache. If the chunks ahead aren't there, that's okay, we just can't
        # cache them. We still keep reading to see if chunks after them are
        # there, since the image is sparse.
        try:
          if name not in self.chunk_cache:
            urn = aff4.ROOT_URN.Add("blobs").Add(name.encode("hex"))
            readahead[urn] = name
        except aff4.ChunkNotFoundError:
          pass

      fds = aff4.FACTORY.MultiOpen(readahead, mode="r", token=self.token)
      for fd in fds:
        name = readahead[fd.urn]

        # Remember the right fd
        if name == chunk_name:
          result = fd

        # Put back into the cache
        self.chunk_cache.Put(readahead[fd.urn], fd)

      if result is None:
        raise aff4.ChunkNotFoundError("Chunk '%s' (urn: %s) not "
                                      "found for reading!"
                                      % (chunk, chunk_name))

    return result

  def _ReadPartial(self, length):
    """Read as much as possible, but not more than length."""
    chunk = self.offset / self.chunksize
    chunk_offset = self.offset % self.chunksize

    # If we're past the end of the file, we don't have a chunk to read from, so
    # we can't read anymore. We return the empty string here so we can read off
    # the end of a file without raising, and get as much data as is there.
    if chunk > self.index.last_chunk:
      return ""

    available_to_read = min(length, self.chunksize - chunk_offset)

    fd = self._GetChunkForReading(chunk)

    fd.Seek(chunk_offset)

    result = fd.Read(available_to_read)
    self.offset += len(result)

    return result

  def AddBlob(self, blob_hash, length, chunk_number):
    """Add another blob to this image using its hash."""

    # TODO(user) Allow the index's chunksize to be > self._HASH_SIZE.
    # This will reduce the number of rows we need to store in the datastore.
    # We'll fill chunks with 0s when we don't have enough information to write
    # to them fully, and ignore 0s when we're reading chunks.

    # There's one hash in the index for each chunk in the file.
    offset = chunk_number * self.index.chunksize
    self.index.Seek(offset)

    # If we're adding a new blob, we should increase the size. If we're just
    # updating an existing blob, the size should stay the same.
    # That is, if we read the index at the right offset and no hash is there, we
    # must not have seen this blob before, so we say we're adding a new one and
    # increase in size.
    if not self.index.ChunkExists(chunk_number):
      # We say that we've increased in size by the size of the blob,
      # but really we only store its hash in the AFF4SparseImage.
      self.size += length

    # Seek back in case we've read past the offset we're meant to write to.
    self.index.Seek(offset)
    self.index.Write(blob_hash)

    self._dirty = True

  def Flush(self, sync=True):
    if self._dirty:
      self.index.Flush(sync=sync)
    super(AFF4SparseImage, self).Flush(sync=sync)


class AFF4SparseIndex(aff4.AFF4Image):
  """A sparse index for AFF4SparseImage."""

  # TODO(user) Allow for a bigger chunk size. At the moment, the
  # chunksize must be exactly the hash size.

  chunksize = 32

  class SchemaCls(aff4.AFF4Image.SchemaCls):
    _CHUNKSIZE = aff4.Attribute("aff4:chunksize", rdfvalue.RDFInteger,
                                "Total size of each chunk.", default=32)
    LAST_CHUNK = aff4.Attribute("aff4:lastchunk", rdfvalue.RDFInteger,
                                "The highest numbered chunk in this object.",
                                default=-1)

  def Initialize(self):
    # The rightmost chunk we've seen so far. We'll use this to keep track of
    # what the biggest possible size this file could be is.
    self.last_chunk = self.Get(self.Schema.LAST_CHUNK)
    super(AFF4SparseIndex, self).Initialize()

  def _GetChunkForWriting(self, chunk):
    """Look in the datastore for a chunk, and create it if it isn't there."""
    chunk_name = self.urn.Add(self.CHUNK_ID_TEMPLATE % chunk)
    try:
      fd = self.chunk_cache.Get(chunk_name)
    except KeyError:
      # Try and get a lock on the chunk.
      fd = aff4.FACTORY.OpenWithLock(chunk_name, token=self.token)
      # If the chunk didn't exist in the datastore, create it.
      if fd.Get(fd.Schema.LAST) is None:
        # Each time we create a new chunk, we grow in size.
        self.size += self.chunksize
        self._dirty = True
        fd = aff4.FACTORY.Create(chunk_name, "AFF4MemoryStream", mode="rw",
                                 token=self.token)
      self.chunk_cache.Put(chunk_name, fd)

      # Keep track of the biggest chunk_number we've seen so far.
      if chunk > self.last_chunk:
        self.last_chunk = chunk
        self._dirty = True

    return fd

  def ChunkExists(self, chunk_number):
    """Do we have this chunk in the index?"""
    try:
      self._GetChunkForReading(chunk_number)
      return True
    except aff4.ChunkNotFoundError:
      return False

  def Write(self, data):
    """Write data to the file."""
    self._dirty = True
    if not isinstance(data, bytes):
      raise IOError("Cannot write unencoded string.")
    while data:
      data = self._WritePartial(data)

  def Read(self, length):
    """Read a block of data from the file."""
    result = ""

    # The total available size in the file
    length = int(length)
    # Make sure we don't read past the "end" of the file. We say the end is the
    # end of the last chunk. If we do try and read past the end, we should
    # return an empty string.
    # The end of the file is the *end* of the last chunk, so we add one here.
    length = min(length,
                 ((self.last_chunk + 1) * self.chunksize) - self.offset)

    while length > 0:
      data = self._ReadPartial(length)
      if not data:
        break

      length -= len(data)
      result += data

    return result

  def Flush(self, sync=True):
    if self._dirty:
      self.Set(self.Schema.LAST_CHUNK, rdfvalue.RDFInteger(self.last_chunk))
    super(AFF4SparseIndex, self).Flush(sync=sync)


class AFF4Index(aff4.AFF4Object):
  """An aff4 object which manages access to an index.

  This object has no actual attributes, it simply manages the index.
  """

  # Value to put in the cell for index hits.
  PLACEHOLDER_VALUE = "X"

  def __init__(self, urn, **kwargs):
    # Never read anything directly from the table by forcing an empty clone.
    kwargs["clone"] = {}
    super(AFF4Index, self).__init__(urn, **kwargs)

    # We collect index data here until we flush.
    self.to_set = set()
    self.to_delete = set()

  def Flush(self, sync=False):
    """Flush the data to the index."""
    super(AFF4Index, self).Flush(sync=sync)

    # Remove entries from deletion set that are going to be added anyway.
    self.to_delete = self.to_delete.difference(self.to_set)

    # Convert sets into dicts that MultiSet handles.
    to_set = dict(zip(self.to_set, self.PLACEHOLDER_VALUE*len(self.to_set)))

    data_store.DB.MultiSet(self.urn, to_set, to_delete=list(self.to_delete),
                           token=self.token, replace=True, sync=sync)
    self.to_set = set()
    self.to_delete = set()

  def Close(self, sync=False):
    self.Flush(sync=sync)
    super(AFF4Index, self).Close(sync=sync)

  def Add(self, urn, attribute, value):
    """Add the attribute of an AFF4 object to the index.

    Args:
      urn: The URN of the AFF4 object this attribute belongs to.
      attribute: The attribute to add to the index.
      value: The value of the attribute to index.

    Raises:
      RuntimeError: If a bad URN is passed in.
    """
    if not isinstance(urn, rdfvalue.RDFURN):
      raise RuntimeError("Bad urn parameter for index addition.")
    column_name = "index:%s:%s:%s" % (
        attribute.predicate, value.lower(), urn)
    self.to_set.add(column_name)

  def Query(self, attributes, regex, limit=100):
    """Query the index for the attribute.

    Args:
      attributes: A list of attributes to query for.
      regex: The regex to search this attribute.
      limit: A (start, length) tuple of integers representing subjects to
          return. Useful for paging. If its a single integer we take it as the
          length limit (start=0).
    Returns:
      A list of RDFURNs which match the index search.
    """
    # Make the regular expressions.
    regex = regex.lstrip("^")   # Begin and end string matches work because
    regex = regex.rstrip("$")   # they are explicit in the storage.
    regexes = ["index:%s:%s:.*" % (a.predicate, regex.lower())
               for a in attributes]
    start = 0
    try:
      start, length = limit  # pylint: disable=unpacking-non-sequence
    except TypeError:
      length = limit

    # Get all the hits
    index_hits = set()
    for col, _, _ in data_store.DB.ResolveRegex(
        self.urn, regexes, token=self.token,
        timestamp=data_store.DB.ALL_TIMESTAMPS):
      # Extract URN from the column_name.
      index_hits.add(rdfvalue.RDFURN(col.rsplit("aff4:/", 1)[1]))

    hits = []
    for i, hit in enumerate(index_hits):
      if i < start: continue
      hits.append(hit)

      if i >= start + length - 1:
        break

    return hits

  def _QueryRaw(self, regex):
    return set([(x, y) for (y, x, _) in data_store.DB.ResolveRegex(
        self.urn, regex, token=self.token,
        timestamp=data_store.DB.ALL_TIMESTAMPS)])

  def MultiQuery(self, attributes, regexes):
    """Query the index for the attribute, matching multiple regexes at a time.

    Args:
      attributes: A list of attributes to query for.
      regexes: A list of regexes to search the attributes for.
    Returns:
      A dict mapping each matched attribute name to a list of RDFURNs.
    """
    # Make the regular expressions.
    combined_regexes = []
    # Begin and end string matches work because they are explicit in storage.
    regexes = [r.lstrip("^").rstrip("$").lower() for r in regexes]
    for attribute in attributes:
      combined_regexes.append("index:%s:(%s):.*" % (
          attribute.predicate, "|".join(regexes)))

    # Get all the hits
    result = {}
    for col, _, _ in data_store.DB.ResolveRegex(
        self.urn, combined_regexes, token=self.token,
        timestamp=data_store.DB.ALL_TIMESTAMPS):
      # Extract the attribute name.
      attribute_name = col.split(":")[3]
      # Extract URN from the column_name.
      urn = rdfvalue.RDFURN(col.rsplit("aff4:/", 1)[1])
      result.setdefault(attribute_name, []).append(urn)

    return result

  def DeleteAttributeIndexesForURN(self, attribute, value, urn):
    """Remove all entries for a given attribute referring to a specific urn."""
    if not isinstance(urn, rdfvalue.RDFURN):
      raise RuntimeError("Bad urn parameter for index deletion.")
    column_name = "index:%s:%s:%s" % (
        attribute.predicate, value.lower(), urn)
    self.to_delete.add(column_name)


class AFF4IndexSet(aff4.AFF4Object):
  """Index that behaves as a set of strings."""

  PLACEHOLDER_VALUE = "X"
  INDEX_PREFIX = "index:"
  INDEX_PREFIX_LEN = len(INDEX_PREFIX)

  def Initialize(self):
    super(AFF4IndexSet, self).Initialize()
    self.to_set = {}
    self.to_delete = set()

  def Add(self, value):
    column_name = self.INDEX_PREFIX + utils.SmartStr(value)
    self.to_set[column_name] = self.PLACEHOLDER_VALUE

  def Remove(self, value):
    column_name = self.INDEX_PREFIX + utils.SmartStr(value)
    self.to_delete.add(column_name)

  def ListValues(self, regex=".*", limit=10000):
    values = data_store.DB.ResolveRegex(self.urn, self.INDEX_PREFIX + regex,
                                        token=self.token)

    result = set()
    for v in values:
      column_name = v[0]
      if column_name in self.to_delete:
        continue

      result.add(column_name[self.INDEX_PREFIX_LEN:])

    for column_name in self.to_set:
      if column_name in self.to_delete:
        continue

      result.add(column_name[self.INDEX_PREFIX_LEN:])

    return result

  def Flush(self, sync=False):
    super(AFF4IndexSet, self).Flush(sync=sync)

    data_store.DB.MultiSet(self.urn, self.to_set, token=self.token,
                           to_delete=list(self.to_delete), replace=True,
                           sync=sync)
    self.to_set = {}
    self.to_delete = set()

  def Close(self, sync=False):
    self.Flush(sync=sync)

    super(AFF4IndexSet, self).Close(sync=sync)


class AFF4LabelsIndex(aff4.AFF4Volume):
  """Index for objects' labels with vaiorus querying capabilities."""

  def Initialize(self):
    super(AFF4LabelsIndex, self).Initialize()

    self._urns_index = None
    self._used_labels_index = None

  @property
  def urns_index(self):
    if self._urns_index is None:
      self._urns_index = aff4.FACTORY.Create(
          self.urn.Add("urns_index"), "AFF4Index", mode=self.mode,
          token=self.token)

    return self._urns_index

  @property
  def used_labels_index(self):
    if self._used_labels_index is None:
      self._used_labels_index = aff4.FACTORY.Create(
          self.urn.Add("used_labels_index"), "AFF4IndexSet", mode=self.mode,
          token=self.token)

    return self._used_labels_index

  def IndexNameForLabel(self, label_name, label_owner):
    return label_owner +  "." + label_name

  def LabelForIndexName(self, index_name):
    label_owner, label_name = utils.SmartStr(index_name).split(".", 1)
    return rdfvalue.AFF4ObjectLabel(name=label_name, owner=label_owner)

  def AddLabel(self, urn, label_name, owner=None):
    if owner is None:
      raise ValueError("owner can't be None")

    index_name = self.IndexNameForLabel(label_name, owner)
    self.urns_index.Add(urn, aff4.AFF4Object.SchemaCls.LABELS, index_name)
    self.used_labels_index.Add(index_name)

  def RemoveLabel(self, urn, label_name, owner=None):
    if owner is None:
      raise ValueError("owner can't be None")

    self.urns_index.DeleteAttributeIndexesForURN(
        aff4.AFF4Object.SchemaCls.LABELS,
        self.IndexNameForLabel(label_name, owner), urn)

  def ListUsedLabels(self):
    index_results = self.used_labels_index.ListValues()
    return [self.LabelForIndexName(name) for name in index_results]

  def FindUrnsByLabel(self, label, owner=None):
    results = self.MultiFindUrnsByLabel([label], owner=owner).values()
    if not results:
      return []
    else:
      return results[0]

  def MultiFindUrnsByLabel(self, labels, owner=None):
    if owner is None:
      owner = ".+?"
    else:
      owner = re.escape(owner)

    query_results = self.urns_index.MultiQuery(
        [aff4.AFF4Object.SchemaCls.LABELS],
        [owner + "\\." + re.escape(label) for label in labels])

    results = {}
    for key, value in query_results.iteritems():
      results[self.LabelForIndexName(key)] = value
    return results

  def FindUrnsByLabelNameRegex(self, label_name_regex, owner=None):
    return self.MultiFindUrnsByLabelNameRegex([label_name_regex], owner=owner)

  def MultiFindUrnsByLabelNameRegex(self, label_name_regexes, owner=None):
    if owner is None:
      owner = ".+?"
    else:
      owner = re.escape(owner)

    query_results = self.urns_index.MultiQuery(
        [aff4.AFF4Object.SchemaCls.LABELS],
        [owner + "\\." + regex
         for regex in label_name_regexes])

    results = {}
    for key, value in query_results.iteritems():
      results[self.LabelForIndexName(key)] = value
    return results

  def CleanUpUsedLabelsIndex(self):
    raise NotImplementedError()

  def Flush(self, sync=False):
    super(AFF4LabelsIndex, self).Flush(sync=sync)

    self.urns_index.Flush(sync=sync)
    self.used_labels_index.Flush(sync=sync)

  def Close(self, sync=False):
    self.Flush(sync=sync)

    super(AFF4LabelsIndex, self).Close(sync=sync)


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
