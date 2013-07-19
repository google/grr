#!/usr/bin/env python
# Copyright 2011 Google Inc. All Rights Reserved.
"""These are standard aff4 objects."""


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

  def Query(self, filter_string="", filter_obj=None, limit=1000,
            age=aff4.NEWEST_TIME):
    """This queries the Directory using a filter expression."""

    direct_children_filter = data_store.DB.filter.SubjectContainsFilter(
        "%s/[^/]+$" % utils.EscapeRegex(self.urn))

    if not filter_string and filter_obj is None:
      filter_obj = direct_children_filter
    elif filter_obj:
      filter_obj = data_store.DB.filter.AndFilter(
          filter_obj, direct_children_filter)
    else:
      # Parse the query string.
      ast = aff4.AFF4QueryParser(filter_string).Parse()
      filter_obj = data_store.DB.filter.AndFilter(
          ast.Compile(data_store.DB.filter),
          direct_children_filter)

    return super(VFSDirectory, self).Query(filter_obj=filter_obj, limit=limit,
                                           age=age)

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

        flow_id = flow.GRRFlow.StartFlow(client_id, "ListDirectory",
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
    if self.dirty:
      self.Set(self.Schema.SIZE(self.size))

    if self.index:
      self.index.Close(sync)
    super(HashImage, self).Close(sync)

  def AddBlob(self, blob_hash, length):
    """Add another blob to this image using its hash."""
    self._OpenIndex()
    self.dirty = True
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

  def __init__(self, urn, **kwargs):
    # Never read anything directly from the table by forcing an empty clone.
    kwargs["clone"] = {}
    super(AFF4Index, self).__init__(urn, **kwargs)

    # We collect index data here until we flush.
    self.to_set = {}

  def Close(self):
    """Flush the data to the index."""
    if self.to_set:
      data_store.DB.MultiSet(self.urn, self.to_set, token=self.token,
                             replace=False, sync=False)

  def Add(self, urn, attribute, value):
    """Add the attribute of an AFF4 object to the index.

    Args:
      urn: The URN of the AFF4 object this attribute belongs to.
      attribute: The attribute to add to the index.
      value: The value of the attribute to index.
    """
    attribute_name = "index:%s:%s" % (
        attribute.predicate, utils.SmartStr(value).lower())
    self.to_set[attribute_name] = (utils.SmartStr(urn),)

  def Query(self, attributes, regex, limit=100):
    """Query the index for the attribute.

    Args:
      attributes: A list of attributes to query for.
      regex: The regex to search this attribute.
      limit: A (start, length) tuple of integers representing subjects to
             return. Useful for paging. If its a single integer we take
             it as the length limit (start=0).

    Returns:
      A list of AFF4 objects which match the index search.
    """
    # Make the regular expression.
    regex = ["index:%s:.*%s.*" % (a.predicate, regex.lower())
             for a in attributes]
    start = 0
    try:
      start, length = limit
    except TypeError:
      length = limit

    # Get all the unique hits
    index_hits = set([x for (_, x, _) in data_store.DB.ResolveRegex(
        self.urn, regex, token=self.token,
        timestamp=data_store.DB.ALL_TIMESTAMPS)])
    hits = []
    for i, hit in enumerate(index_hits):
      if i < start: continue
      hits.append(hit)

      if i >= start + length - 1:
        break

    return aff4.FACTORY.MultiOpen(hits, mode=self.mode, token=self.token)
