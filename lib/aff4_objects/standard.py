#!/usr/bin/env python
"""These are standard aff4 objects."""


import hashlib
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
      pathspec = self.Get(self.Schema.PATHSPEC)

      stripped_components = []
      parent = self

      while not pathspec and len(parent.urn.Split()) > 1:
        # We try to recurse up the tree to get a real pathspec.
        # These directories are created automatically without pathspecs when a
        # deep directory is listed without listing the parents.
        # Note /fs/os or /fs/tsk won't be updateable so we will raise IOError
        # if we try.
        stripped_components.append(parent.urn.Basename())
        pathspec = parent.Get(parent.Schema.PATHSPEC)
        parent = aff4.FACTORY.Open(parent.urn.Dirname(), token=self.token)

      if pathspec:
        if stripped_components:
          # We stripped pieces of the URL, time to add them back at the deepest
          # nested path.
          new_path = utils.JoinPath(pathspec.last.path,
                                    *stripped_components[:-1])
          pathspec.last.path = new_path

        flow_id = flow.GRRFlow.StartFlow(client_id=client_id,
                                         flow_name="ListDirectory",
                                         pathspec=pathspec, priority=priority,
                                         notify_to_user=False,
                                         token=self.token)
      else:
        raise IOError("Item has no pathspec.")

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
                                 "Protodict containing arrays of hashes.")

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
                                 "Protodict containing arrays of hashes.")


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
    to_delete = dict(zip(self.to_delete,
                         self.PLACEHOLDER_VALUE*len(self.to_delete)))
    to_set = dict(zip(self.to_set, self.PLACEHOLDER_VALUE*len(self.to_set)))

    data_store.DB.MultiSet(self.urn, to_set, to_delete=to_delete,
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
    regexes = ["index:%s:%s:.*" % (a.predicate, regex.lower())
               for a in attributes]
    start = 0
    try:
      start, length = limit
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

  def DeleteAttributeIndexesForURN(self, attribute, value, urn):
    """Remove all entries for a given attribute referring to a specific urn."""
    if not isinstance(urn, rdfvalue.RDFURN):
      raise RuntimeError("Bad urn parameter for index deletion.")
    column_name = "index:%s:%s:%s" % (
        attribute.predicate, value.lower(), urn)
    self.to_delete.add(column_name)


class TempFile(aff4.AFF4MemoryStream):
  """A temporary file (with a random URN) to store an RDFValue."""

  def __init__(self, urn, **kwargs):
    if urn is None:
      urn = rdfvalue.RDFURN("aff4:/tmp").Add("%X" % utils.PRNG.GetULong())

    super(TempFile, self).__init__(urn, **kwargs)
