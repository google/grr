#!/usr/bin/env python
"""REL_DB-based file store implementation."""
from __future__ import absolute_import
from __future__ import division

from __future__ import unicode_literals

import abc
import collections
import hashlib
import io
import os

from future.utils import iteritems
from future.utils import iterkeys
from future.utils import with_metaclass

from typing import Dict
from typing import Iterable
from typing import NamedTuple

from grr_response_core import config
from grr_response_core.lib import utils
from grr_response_core.lib.util import collection
from grr_response_core.lib.util import precondition
from grr_response_server import data_store
from grr_response_server.databases import db
from grr_response_server.rdfvalues import objects as rdf_objects


class Error(Exception):
  """FileStore-related error class."""


class BlobNotFoundError(Error):
  """Raised when a blob was expected to exist, but couldn't be found."""


class FileHasNoContentError(Error):
  """Raised when trying to read a file that was never downloaded."""

  def __init__(self, path):
    super(FileHasNoContentError,
          self).__init__("File was never collected: %r" % (path,))


class MissingBlobReferencesError(Error):
  """Raised when blob refs are supposed to be there but couldn't be found."""


class OversizedReadError(Error):
  """Raises when trying to read large files without specifying read length."""


FileMetadata = NamedTuple("FileMetadata", [
    ("client_path", db.ClientPath),
    ("blob_refs", Iterable[rdf_objects.BlobReference]),
])


class ExternalFileStore(with_metaclass(abc.ABCMeta, object)):
  """Filestore for files collected from clients."""

  @abc.abstractmethod
  def AddFile(self, hash_id, metadata):
    """Add a new file to the file store."""
    raise NotImplementedError()

  def AddFiles(self, hash_id_metadatas):
    """Adds multiple files to the file store.

    Args:
      hash_id_metadatas: A dictionary mapping hash ids to file metadata (a tuple
        of hash client path and blob references).
    """
    for hash_id, metadata in iteritems(hash_id_metadatas):
      self.AddFile(hash_id, metadata)


class CompositeExternalFileStore(ExternalFileStore):
  """Composite file store used to multiplex requests to multiple file stores."""

  def __init__(self, nested_stores=None):
    super(CompositeExternalFileStore, self).__init__()

    self.nested_stores = nested_stores or []

  def RegisterFileStore(self, fs):
    if not isinstance(fs, ExternalFileStore):
      raise TypeError("Can only register objects of classes inheriting "
                      "from ExternalFileStore.")

    self.nested_stores.append(fs)

  def AddFile(self, hash_id, metadata):
    for fs in self.nested_stores:
      fs.AddFile(hash_id, metadata)

  def AddFiles(self, hash_id_metadatas):
    for nested_store in self.nested_stores:
      nested_store.AddFiles(hash_id_metadatas)


EXTERNAL_FILE_STORE = CompositeExternalFileStore()


# TODO(user): this is a naive implementation as it reads one chunk
# per REL_DB call. It has to be optimized.
class BlobStream(object):
  """File-like object for reading from blobs."""

  def __init__(self, client_path, blob_refs, hash_id):
    self._client_path = client_path
    self._blob_refs = blob_refs
    self._hash_id = hash_id

    self._max_unbound_read = config.CONFIG["Server.max_unbound_read_size"]

    self._offset = 0
    self._length = self._blob_refs[-1].offset + self._blob_refs[-1].size

    self._current_ref = None
    self._current_chunk = None

  def _GetChunk(self):
    """Fetches a chunk corresponding to the current offset."""

    found_ref = None
    for ref in self._blob_refs:
      if self._offset >= ref.offset and self._offset < (ref.offset + ref.size):
        found_ref = ref
        break

    if not found_ref:
      return None, None

    # If self._current_ref == found_ref, then simply return previously found
    # chunk. Otherwise, update self._current_chunk value.
    if self._current_ref != found_ref:
      self._current_ref = found_ref

      data = data_store.BLOBS.ReadBlobs([found_ref.blob_id])
      self._current_chunk = data[found_ref.blob_id]

    return self._current_chunk, self._current_ref

  def Read(self, length=None):
    """Reads data."""

    if length is None:
      length = self._length - self._offset

    if length > self._max_unbound_read:
      raise OversizedReadError("Attempted to read %d bytes when "
                               "Server.max_unbound_read_size is %d" %
                               (length, self._max_unbound_read))

    result = io.BytesIO()
    while result.tell() < length:
      chunk, ref = self._GetChunk()
      if not chunk:
        break

      part = chunk[self._offset - ref.offset:]
      if not part:
        break

      result.write(part)
      self._offset += min(length, len(part))

    return result.getvalue()[:length]

  def Tell(self):
    """Returns current reading cursor position."""

    return self._offset

  def Seek(self, offset, whence=os.SEEK_SET):
    """Moves the reading cursor."""

    if whence == os.SEEK_SET:
      self._offset = offset
    elif whence == os.SEEK_CUR:
      self._offset += offset
    elif whence == os.SEEK_END:
      self._offset = self._length + offset
    else:
      raise ValueError("Invalid whence argument: %s" % whence)

  read = utils.Proxy("Read")
  tell = utils.Proxy("Tell")
  seek = utils.Proxy("Seek")

  @property
  def size(self):
    """Size of the hashed data."""
    return self._length

  @property
  def hash_id(self):
    """Hash ID identifying hashed data."""
    return self._hash_id

  def Path(self):
    return self._client_path.Path()


_BLOBS_READ_BATCH_SIZE = 200


def AddFilesWithUnknownHashes(
    client_path_blob_refs,
    use_external_stores = True
):
  """Adds new files consisting of given blob references.

  Args:
    client_path_blob_refs: A dictionary mapping `db.ClientPath` instances to
      lists of blob references.
    use_external_stores: A flag indicating if the files should also be added to
      external file stores.

  Returns:
    A dictionary mapping `db.ClientPath` to hash ids of the file.

  Raises:
    BlobNotFoundError: If one of the referenced blobs cannot be found.
  """
  hash_id_blob_refs = dict()
  client_path_hash_id = dict()
  metadatas = dict()

  all_client_path_blob_refs = list()
  for client_path, blob_refs in iteritems(client_path_blob_refs):
    # In the special case where there is only one blob, we don't need to go to
    # the data store to read said blob and rehash it, we have all that
    # information already available. For empty files without blobs, we can just
    # hash the empty string instead.
    if len(blob_refs) <= 1:
      if blob_refs:
        hash_id = rdf_objects.SHA256HashID.FromBytes(
            blob_refs[0].blob_id.AsBytes())
      else:
        hash_id = rdf_objects.SHA256HashID.FromData(b"")

      client_path_hash_id[client_path] = hash_id
      hash_id_blob_refs[hash_id] = blob_refs
      metadatas[hash_id] = FileMetadata(
          client_path=client_path, blob_refs=blob_refs)
    else:
      for blob_ref in blob_refs:
        all_client_path_blob_refs.append((client_path, blob_ref))

  client_path_offset = collections.defaultdict(lambda: 0)
  client_path_sha256 = collections.defaultdict(hashlib.sha256)
  verified_client_path_blob_refs = collections.defaultdict(list)

  client_path_blob_ref_batches = collection.Batch(
      items=all_client_path_blob_refs, size=_BLOBS_READ_BATCH_SIZE)

  for client_path_blob_ref_batch in client_path_blob_ref_batches:
    blob_id_batch = set(
        blob_ref.blob_id for _, blob_ref in client_path_blob_ref_batch)
    blobs = data_store.BLOBS.ReadBlobs(blob_id_batch)

    for client_path, blob_ref in client_path_blob_ref_batch:
      blob = blobs[blob_ref.blob_id]
      if blob is None:
        message = "Could not find one of referenced blobs: {}".format(
            blob_ref.blob_id)
        raise BlobNotFoundError(message)

      offset = client_path_offset[client_path]
      if blob_ref.size != len(blob):
        raise ValueError(
            "Got conflicting size information for blob %s: %d vs %d." %
            (blob_ref.blob_id, blob_ref.size, len(blob)))
      if blob_ref.offset != offset:
        raise ValueError(
            "Got conflicting offset information for blob %s: %d vs %d." %
            (blob_ref.blob_id, blob_ref.offset, offset))

      verified_client_path_blob_refs[client_path].append(blob_ref)
      client_path_offset[client_path] = offset + len(blob)
      client_path_sha256[client_path].update(blob)

  for client_path in iterkeys(client_path_sha256):
    sha256 = client_path_sha256[client_path].digest()
    hash_id = rdf_objects.SHA256HashID.FromBytes(sha256)

    client_path_hash_id[client_path] = hash_id
    hash_id_blob_refs[hash_id] = verified_client_path_blob_refs[client_path]

  data_store.REL_DB.WriteHashBlobReferences(hash_id_blob_refs)

  if use_external_stores:
    for client_path in iterkeys(verified_client_path_blob_refs):
      metadatas[client_path_hash_id[client_path]] = FileMetadata(
          client_path=client_path,
          blob_refs=verified_client_path_blob_refs[client_path])

    EXTERNAL_FILE_STORE.AddFiles(metadatas)

  return client_path_hash_id


def AddFileWithUnknownHash(client_path, blob_refs, use_external_stores=True):
  """Add a new file consisting of given blob IDs."""
  precondition.AssertType(client_path, db.ClientPath)
  precondition.AssertIterableType(blob_refs, rdf_objects.BlobReference)
  return AddFilesWithUnknownHashes(
      {client_path: blob_refs},
      use_external_stores=use_external_stores)[client_path]


def CheckHashes(hash_ids):
  """Checks if files with given hashes are present in the file store.

  Args:
    hash_ids: A list of SHA256HashID objects.

  Returns:
    A dict where SHA256HashID objects are keys. Corresponding values
    may be False (if hash id is not present) or True if it is not present.
  """
  return {
      k: bool(v)
      for k, v in data_store.REL_DB.ReadHashBlobReferences(hash_ids).items()
  }


def GetLastCollectionPathInfos(client_paths, max_timestamp=None):
  """Returns PathInfos corresponding to last collection times.

  Args:
    client_paths: An iterable of ClientPath objects.
    max_timestamp: When specified, onlys PathInfo with a timestamp lower or
      equal to max_timestamp will be returned.

  Returns:
    A dict of ClientPath -> PathInfo where each PathInfo corresponds to a
    collected
    file. PathInfo may be None if no collection happened (ever or with a
    timestamp
    lower or equal then max_timestamp).
  """
  return data_store.REL_DB.ReadLatestPathInfosWithHashBlobReferences(
      client_paths, max_timestamp=max_timestamp)


def GetLastCollectionPathInfo(client_path, max_timestamp=None):
  """Returns PathInfo corresponding to the last file collection time.

  Args:
    client_path: A ClientPath object.
    max_timestamp: When specified, the returned PathInfo will correspond to the
      latest file collection with a timestamp lower or equal to max_timestamp.

  Returns:
    PathInfo object corresponding to the latest collection or None if file
    wasn't collected (ever or, when max_timestamp is specified, before
    max_timestamp).
  """

  return GetLastCollectionPathInfos([client_path],
                                    max_timestamp=max_timestamp)[client_path]


def OpenFile(client_path, max_timestamp=None):
  """Opens latest content of a given file for reading.

  Args:
    client_path: A db.ClientPath object describing path to a file.
    max_timestamp: If specified, will open the last collected version with a
      timestamp equal or lower than max_timestamp. If not specified, will simply
      open the latest version.

  Returns:
    A file like object with random access support.

  Raises:
    FileHasNoContentError: if the file was never collected.
    MissingBlobReferencesError: if one of the blobs was not found.
  """

  path_info = data_store.REL_DB.ReadLatestPathInfosWithHashBlobReferences(
      [client_path], max_timestamp=max_timestamp)[client_path]

  if path_info is None:
    raise FileHasNoContentError(client_path)

  hash_id = rdf_objects.SHA256HashID.FromBytes(
      path_info.hash_entry.sha256.AsBytes())
  blob_references = data_store.REL_DB.ReadHashBlobReferences([hash_id])[hash_id]

  if blob_references is None:
    raise MissingBlobReferencesError(
        "File hash was expected to have corresponding "
        "blob references, but they were not found: %r" % hash_id)

  return BlobStream(client_path, blob_references, hash_id)


STREAM_CHUNKS_READ_AHEAD = 500


class StreamedFileChunk(object):
  """An object representing a single streamed file chunk."""

  def __init__(self, client_path, data, chunk_index, total_chunks, offset,
               total_size):
    """Initializes StreamedFileChunk object.

    Args:
      client_path: db.ClientPath identifying the file.
      data: bytes with chunk's contents.
      chunk_index: Index of this chunk (relative to the sequence of chunks
        corresponding to the file).
      total_chunks: Total number of chunks corresponding to a given file.
      offset: Offset of this chunk in bytes from the beginning of the file.
      total_size: Total size of the file in bytes.
    """
    self.client_path = client_path
    self.data = data
    self.offset = offset
    self.total_size = total_size
    self.chunk_index = chunk_index
    self.total_chunks = total_chunks


def StreamFilesChunks(client_paths, max_timestamp=None, max_size=None):
  """Streams contents of given files.

  Args:
    client_paths: db.ClientPath objects describing paths to files.
    max_timestamp: If specified, then for every requested file will open the
      last collected version of the file with a timestamp equal or lower than
      max_timestamp. If not specified, will simply open a latest version for
      each file.
    max_size: If specified, only the chunks covering max_size bytes will be
      returned.

  Yields:
    StreamedFileChunk objects for every file read. Chunks will be returned
    sequentially, their order will correspond to the client_paths order.
    Files having no content will simply be ignored.
  """

  path_infos_by_cp = (
      data_store.REL_DB.ReadLatestPathInfosWithHashBlobReferences(
          client_paths, max_timestamp=max_timestamp))

  hash_ids_by_cp = {
      cp: rdf_objects.SHA256HashID.FromBytes(pi.hash_entry.sha256.AsBytes())
      for cp, pi in iteritems(path_infos_by_cp)
      if pi
  }

  blob_refs_by_hash_id = data_store.REL_DB.ReadHashBlobReferences(
      hash_ids_by_cp.values())

  all_chunks = []
  for cp in client_paths:
    try:
      hash_id = hash_ids_by_cp[cp]
    except KeyError:
      continue

    try:
      blob_refs = blob_refs_by_hash_id[hash_id]
    except KeyError:
      continue

    num_blobs = len(blob_refs)
    total_size = 0
    for ref in blob_refs:
      total_size += ref.size

    cur_size = 0
    for i, ref in enumerate(blob_refs):
      all_chunks.append((cp, ref.blob_id, i, num_blobs, ref.offset, total_size))

      cur_size += ref.size
      if max_size is not None and cur_size >= max_size:
        break

  for batch in collection.Batch(all_chunks, STREAM_CHUNKS_READ_AHEAD):
    blobs = data_store.BLOBS.ReadBlobs(
        [blob_id for cp, blob_id, i, num_blobs, offset, total_size in batch])
    for cp, blob_id, i, num_blobs, offset, total_size in batch:
      yield StreamedFileChunk(cp, blobs[blob_id], i, num_blobs, offset,
                              total_size)
