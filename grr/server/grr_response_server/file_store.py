#!/usr/bin/env python
"""REL_DB-based file store implementation."""

import abc
import collections
from collections.abc import Sequence
import hashlib
import io
import os
from typing import Collection, Dict, Iterable, NamedTuple, Optional

from grr_response_core import config
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.util import collection
from grr_response_core.lib.util import precondition
from grr_response_server import data_store
from grr_response_server.databases import db
from grr_response_server.models import blobs as models_blob
from grr_response_server.rdfvalues import mig_objects
from grr_response_server.rdfvalues import objects as rdf_objects


class Error(Exception):
  """FileStore-related error class."""


class BlobNotFoundError(Error):
  """Raised when a blob was expected to exist, but couldn't be found."""

  def __init__(self, blob_id: models_blob.BlobID) -> None:
    super().__init__(
        "Could not find one of referenced blobs: {}. "
        "This is a sign of datastore inconsistency".format(blob_id)
    )


# TODO(hanuszczak): Fix the linter warning properly.
class FileNotFoundError(Error):  # pylint: disable=redefined-builtin
  """Raised when a given file path is not present in the datastore."""

  def __init__(self, client_path):
    super().__init__("File not found: {}.".format(client_path))


class FileHasNoContentError(Error):
  """Raised when trying to read a file that was never downloaded."""

  def __init__(self, client_path: db.ClientPath) -> None:
    super().__init__("File was never collected: %r" % (client_path,))


class MissingBlobReferencesError(Error):
  """Raised when blob refs are supposed to be there but couldn't be found."""


class OversizedReadError(Error):
  """Raises when trying to read large files without specifying read length."""


class InvalidBlobSizeError(Error):
  """Raised when actual blob size differs from an expected one."""


class InvalidBlobOffsetError(Error):
  """Raised when actual blob offset differs from an expected one."""


FileMetadata = NamedTuple(
    "FileMetadata",
    [
        ("client_path", db.ClientPath),
        ("blob_refs", Iterable[rdf_objects.BlobReference]),
    ],
)


class ExternalFileStore(metaclass=abc.ABCMeta):
  """Filestore for files collected from clients."""

  @abc.abstractmethod
  def AddFile(self, hash_id: rdf_objects.HashID, metadata: FileMetadata):
    """Add a new file to the file store."""
    raise NotImplementedError()

  def AddFiles(self, hash_id_metadatas: Dict[rdf_objects.HashID, FileMetadata]):
    """Adds multiple files to the file store.

    Args:
      hash_id_metadatas: A dictionary mapping hash ids to file metadata (a tuple
        of hash client path and blob references).
    """
    for hash_id, metadata in hash_id_metadatas.items():
      self.AddFile(hash_id, metadata)


class CompositeExternalFileStore(ExternalFileStore):
  """Composite file store used to multiplex requests to multiple file stores."""

  def __init__(self, nested_stores=None):
    super().__init__()

    self.nested_stores = nested_stores or []

  def RegisterFileStore(self, fs: ExternalFileStore) -> None:
    if not isinstance(fs, ExternalFileStore):
      raise TypeError(
          "Can only register objects of classes inheriting "
          "from ExternalFileStore."
      )

    self.nested_stores.append(fs)

  def AddFile(
      self,
      hash_id: rdf_objects.HashID,
      metadata: FileMetadata,
  ) -> None:
    for fs in self.nested_stores:
      fs.AddFile(hash_id, metadata)

  def AddFiles(
      self, hash_id_metadatas: Dict[rdf_objects.HashID, FileMetadata]
  ) -> None:
    for nested_store in self.nested_stores:
      nested_store.AddFiles(hash_id_metadatas)


EXTERNAL_FILE_STORE = CompositeExternalFileStore()


# TODO(user): this is a naive implementation as it reads one chunk
# per REL_DB call. It has to be optimized.
class BlobStream:
  """File-like object for reading from blobs."""

  def __init__(
      self,
      client_path: db.ClientPath,
      blob_refs: Sequence[rdf_objects.BlobReference],
      hash_id: Optional[rdf_objects.HashID],
  ) -> None:
    self._client_path = client_path
    self._blob_refs = blob_refs
    self._hash_id = hash_id

    self._max_unbound_read = config.CONFIG["Server.max_unbound_read_size"]

    self._offset = 0
    self._length = 0
    if self._blob_refs:
      self._length = self._blob_refs[-1].offset + self._blob_refs[-1].size

    self._current_ref = None
    self._current_chunk = None

  def _GetChunk(
      self,
  ) -> tuple[Optional[bytes], Optional[rdf_objects.BlobReference]]:
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

      blob_id = models_blob.BlobID(found_ref.blob_id)
      data = data_store.BLOBS.ReadBlobs([blob_id])
      if data[blob_id] is None:
        raise BlobNotFoundError(blob_id)
      self._current_chunk = data[blob_id]

    return self._current_chunk, self._current_ref

  def Read(self, length: Optional[int] = None) -> bytes:
    """Reads data."""

    if length is None:
      length = self._length - self._offset

      # Only enforce limit when length is not specified manually.
      if length > self._max_unbound_read:
        raise OversizedReadError(
            "Attempted to read %d bytes when Server.max_unbound_read_size is %d"
            % (length, self._max_unbound_read)
        )

    result = io.BytesIO()
    while result.tell() < length:
      chunk, ref = self._GetChunk()
      if not chunk or not ref:
        break

      part = chunk[self._offset - ref.offset :]
      if not part:
        break

      result.write(part)
      self._offset += min(length, len(part))

    return result.getvalue()[:length]

  def Tell(self) -> int:
    """Returns current reading cursor position."""

    return self._offset

  def Seek(self, offset: int, whence=os.SEEK_SET) -> None:
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
  def size(self) -> int:
    """Size of the hashed data."""
    return self._length

  @property
  def hash_id(self) -> Optional[rdf_objects.HashID]:
    """Hash ID identifying hashed data."""
    return self._hash_id

  def Path(self) -> str:
    return self._client_path.Path()


_BLOBS_READ_BATCH_SIZE = 200

BLOBS_READ_TIMEOUT = rdfvalue.Duration.From(120, rdfvalue.SECONDS)


def AddFilesWithUnknownHashes(
    client_path_blob_refs: Dict[
        db.ClientPath, Iterable[rdf_objects.BlobReference]
    ],
    use_external_stores: bool = True,
) -> Dict[db.ClientPath, rdf_objects.SHA256HashID]:
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
    InvalidBlobSizeError: if reference's blob size is different from an
        actual blob size.
    InvalidBlobOffsetError: if reference's blob offset is different from an
        actual blob offset.
  """
  hash_id_blob_refs = dict()
  client_path_hash_id = dict()
  metadatas = dict()

  all_client_path_blob_refs = list()
  for client_path, blob_refs in client_path_blob_refs.items():
    if blob_refs:
      for blob_ref in blob_refs:
        blob_ref = mig_objects.ToProtoBlobReference(blob_ref)
        all_client_path_blob_refs.append((client_path, blob_ref))
    else:
      # Make sure empty files (without blobs) are correctly handled.
      hash_id = rdf_objects.SHA256HashID.FromData(b"")
      client_path_hash_id[client_path] = hash_id
      hash_id_blob_refs[hash_id] = []
      metadatas[hash_id] = FileMetadata(client_path=client_path, blob_refs=[])

  client_path_offset = collections.defaultdict(lambda: 0)
  client_path_sha256 = collections.defaultdict(hashlib.sha256)
  verified_client_path_blob_refs = collections.defaultdict(list)

  client_path_blob_ref_batches = collection.Batch(
      items=all_client_path_blob_refs, size=_BLOBS_READ_BATCH_SIZE
  )

  for client_path_blob_ref_batch in client_path_blob_ref_batches:
    blob_id_batch = set(
        models_blob.BlobID(blob_ref.blob_id)
        for _, blob_ref in client_path_blob_ref_batch
    )
    blobs = data_store.BLOBS.ReadAndWaitForBlobs(
        blob_id_batch, timeout=BLOBS_READ_TIMEOUT
    )

    for client_path, blob_ref in client_path_blob_ref_batch:
      blob = blobs[models_blob.BlobID(blob_ref.blob_id)]
      if blob is None:
        raise BlobNotFoundError(models_blob.BlobID(blob_ref.blob_id))

      offset = client_path_offset[client_path]
      if blob_ref.size != len(blob):
        raise InvalidBlobSizeError(
            "Got conflicting size information for blob %s: %d vs %d."
            % (blob_ref.blob_id, blob_ref.size, len(blob))
        )
      if blob_ref.offset != offset:
        raise InvalidBlobOffsetError(
            "Got conflicting offset information for blob %s: %d vs %d."
            % (blob_ref.blob_id, blob_ref.offset, offset)
        )

      verified_client_path_blob_refs[client_path].append(blob_ref)
      client_path_offset[client_path] = offset + len(blob)
      client_path_sha256[client_path].update(blob)

  for client_path in client_path_sha256.keys():
    sha256 = client_path_sha256[client_path].digest()
    hash_id = rdf_objects.SHA256HashID.FromSerializedBytes(sha256)

    client_path_hash_id[client_path] = hash_id
    hash_id_blob_refs[hash_id] = verified_client_path_blob_refs[client_path]

  data_store.REL_DB.WriteHashBlobReferences(hash_id_blob_refs)

  if use_external_stores:
    for client_path in verified_client_path_blob_refs.keys():
      metadatas[client_path_hash_id[client_path]] = FileMetadata(
          client_path=client_path,
          blob_refs=list(
              map(
                  mig_objects.ToRDFBlobReference,
                  verified_client_path_blob_refs[client_path],
              )
          ),
      )

    EXTERNAL_FILE_STORE.AddFiles(metadatas)

  return client_path_hash_id


def AddFileWithUnknownHash(
    client_path: db.ClientPath,
    blob_refs: Sequence[rdf_objects.BlobReference],
    use_external_stores: bool = True,
) -> rdf_objects.SHA256HashID:
  """Add a new file consisting of given blob IDs."""
  precondition.AssertType(client_path, db.ClientPath)
  precondition.AssertIterableType(blob_refs, rdf_objects.BlobReference)
  return AddFilesWithUnknownHashes(
      {client_path: blob_refs}, use_external_stores=use_external_stores
  )[client_path]


def CheckHashes(
    hash_ids: Collection[rdf_objects.SHA256HashID],
) -> Dict[rdf_objects.SHA256HashID, bool]:
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


def OpenFile(
    client_path: db.ClientPath,
    max_timestamp: Optional[rdfvalue.RDFDatetime] = None,
) -> BlobStream:
  """Opens latest content of a given file for reading.

  Args:
    client_path: A path to a file.
    max_timestamp: If specified, will open the last collected version with a
      timestamp equal or lower than max_timestamp. If not specified, will simply
      open the latest version.

  Returns:
    A file like object with random access support.

  Raises:
    FileHasNoContentError: if the file was never collected.
    MissingBlobReferencesError: if one of the blobs was not found.
  """

  proto_path_info = data_store.REL_DB.ReadLatestPathInfosWithHashBlobReferences(
      [client_path], max_timestamp=max_timestamp
  )[client_path]
  path_info = None
  if proto_path_info:
    path_info = mig_objects.ToRDFPathInfo(proto_path_info)

  if path_info is None:
    # If path_info returned by ReadLatestPathInfosWithHashBlobReferences
    # is None, do one more ReadPathInfo call to check if this path info
    # was ever present in the database.
    try:
      data_store.REL_DB.ReadPathInfo(
          client_path.client_id, client_path.path_type, client_path.components
      )
    except db.UnknownPathError:
      raise FileNotFoundError(client_path)

    # If the given path info is present in the database, but there are
    # no suitable hash blob references associated with it, raise
    # FileHasNoContentError instead of FileNotFoundError.
    raise FileHasNoContentError(client_path)

  hash_id = rdf_objects.SHA256HashID.FromSerializedBytes(
      path_info.hash_entry.sha256.AsBytes()
  )
  blob_references = data_store.REL_DB.ReadHashBlobReferences([hash_id])[hash_id]

  if blob_references is None:
    raise MissingBlobReferencesError(
        "File hash was expected to have corresponding "
        "blob references, but they were not found: %r" % hash_id
    )

  blob_references = list(map(mig_objects.ToRDFBlobReference, blob_references))
  return BlobStream(client_path, blob_references, hash_id)


STREAM_CHUNKS_READ_AHEAD = 500


class StreamedFileChunk:
  """An object representing a single streamed file chunk."""

  def __init__(
      self,
      client_path: db.ClientPath,
      data: bytes,
      chunk_index: int,
      total_chunks: int,
      offset: int,
      total_size: int,
  ) -> None:
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


def StreamFilesChunks(
    client_paths: Collection[db.ClientPath],
    max_timestamp: Optional[rdfvalue.RDFDatetime] = None,
    max_size: Optional[int] = None,
) -> Iterable[StreamedFileChunk]:
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

  Raises:
    BlobNotFoundError: if one of the blobs wasn't found while streaming.
  """

  proto_path_infos_by_cp = (
      data_store.REL_DB.ReadLatestPathInfosWithHashBlobReferences(
          client_paths, max_timestamp=max_timestamp
      )
  )
  path_infos_by_cp = {}
  for k, v in proto_path_infos_by_cp.items():
    path_infos_by_cp[k] = None
    if v is not None:
      path_infos_by_cp[k] = v

  hash_ids_by_cp = {}
  for cp, pi in path_infos_by_cp.items():
    if pi:
      hash_ids_by_cp[cp] = rdf_objects.SHA256HashID.FromSerializedBytes(
          pi.hash_entry.sha256
      )

  blob_refs_by_hash_id = data_store.REL_DB.ReadHashBlobReferences(
      hash_ids_by_cp.values()
  )

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
      blob_id = models_blob.BlobID(ref.blob_id)
      all_chunks.append((cp, blob_id, i, num_blobs, ref.offset, total_size))

      cur_size += ref.size
      if max_size is not None and cur_size >= max_size:
        break

  for batch in collection.Batch(all_chunks, STREAM_CHUNKS_READ_AHEAD):
    blobs = data_store.BLOBS.ReadBlobs(
        [blob_id for _, blob_id, _, _, _, _ in batch]
    )
    for cp, blob_id, i, num_blobs, offset, total_size in batch:
      blob_data = blobs[blob_id]
      if blob_data is None:
        raise BlobNotFoundError(blob_id)

      yield StreamedFileChunk(cp, blob_data, i, num_blobs, offset, total_size)
