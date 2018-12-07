#!/usr/bin/env python
"""REL_DB-based file store implementation."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import abc
import hashlib
import io
import os

from future.utils import iteritems
from future.utils import with_metaclass

from grr_response_core import config
from grr_response_core.lib import utils
from grr_response_core.lib.util import collection
from grr_response_server import data_store
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


class ExternalFileStore(with_metaclass(abc.ABCMeta, object)):
  """Filestore for files collected from clients."""

  @abc.abstractmethod
  def AddFile(self, file_hash, blob_refs):
    """Add a new file to the file store."""
    raise NotImplementedError()


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

  def AddFile(self, file_hash, blob_refs):
    for fs in self.nested_stores:
      fs.AddFile(file_hash, blob_refs)


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


def AddFileWithUnknownHash(blob_ids):
  """Add a new file consisting of given blob IDs."""

  blob_refs = []
  offset = 0
  sha256 = hashlib.sha256()
  for blob_ids_batch in collection.Batch(blob_ids, _BLOBS_READ_BATCH_SIZE):
    unique_ids = set(blob_ids_batch)
    data = data_store.BLOBS.ReadBlobs(unique_ids)
    for k, v in iteritems(data):
      if v is None:
        raise BlobNotFoundError("Couldn't find one of referenced blobs: %s" % k)

    for blob_id in blob_ids_batch:
      blob_data = data[blob_id]
      blob_refs.append(
          rdf_objects.BlobReference(
              offset=offset,
              size=len(blob_data),
              blob_id=blob_id,
          ))
      offset += len(blob_data)

      sha256.update(blob_data)

  hash_id = rdf_objects.SHA256HashID.FromBytes(sha256.digest())
  data_store.REL_DB.WriteHashBlobReferences({hash_id: blob_refs})

  return hash_id


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
