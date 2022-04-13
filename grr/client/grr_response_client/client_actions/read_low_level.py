#!/usr/bin/env python
"""The ReadLowLevel client action."""

import hashlib
import io
from typing import AnyStr, Optional
import zlib

from grr_response_client import actions
from grr_response_client import comms
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_core.lib.rdfvalues import read_low_level as rdf_read_low_level

# We'll read at most 10 GiB in this flow. If the requested length is greater
# than that, we throw an error.
_READ_BYTES_LIMIT = 10 * 1024 * 1024 * 1024  # 10 GiB

# This will be used for sector alignment (align the offset before reading).
# All Windows versions support hard disk drives with 512-byte sectors.
# We use this value by default, but if the device has a different block size,
# the user can set it in the args.
_DEFAULT_SECTOR_BLOCK_SIZE = 512

# We'll read chunks of `DEFAULT_BLOB_SIZE` at a time when possible, and hash
# and store them in BlobStore. The BlobIDs will be sent back to the flow.
# 4 MiB ia a good size for chunks to be sent to BlobStore efficiently.
_DEFAULT_BLOB_SIZE = 4 * 1024 * 1024  # 4 MiB


class ReadLowLevel(actions.ActionPlugin):
  """Reads `length` bytes from `path` starting at `offset` and returns it."""

  in_rdfvalue = rdf_read_low_level.ReadLowLevelRequest
  out_rdfvalues = [rdf_read_low_level.ReadLowLevelResult]

  def __init__(self, grr_worker: Optional[comms.GRRClientWorker] = None):
    super().__init__(grr_worker)

    # Extra amount of bytes to be read in case the `offset` is misaligned, or
    # the `length` to be read is not aligned with the block size. This will be
    # used for updating the `offset` before the read (client action args). It
    # will also be later discarded from the `data` read.
    self._pre_padding = 0

    # Stores a partial file hash for all data read so far.
    self._partial_file_hash = hashlib.sha256()

  def Run(self, args: rdf_read_low_level.ReadLowLevelRequest) -> None:
    """Reads a buffer, stores it and sends it back to the server."""

    # Make sure we limit the size of our output.
    if args.length > _READ_BYTES_LIMIT:
      raise RuntimeError(f"Can not read buffers this large "
                         f"({args.length} > {_READ_BYTES_LIMIT} bytes).")

    # TODO: Update `blob_size` when `sector_block_size` is set.
    # `blob_size` must be a multiple of `sector_block_size` so that reads start
    # and _continue_ to be aligned.
    # An alternative is to _always_ align (each blob read).
    blob_size = args.blob_size or _DEFAULT_BLOB_SIZE
    pre_padding = GetPrePadding(args)
    self._pre_padding = pre_padding
    aligned_args = AlignArgs(args, pre_padding)

    bytes_left_to_read = aligned_args.length
    is_first_chunk = True
    current_offset = aligned_args.offset

    with open(args.path, "rb") as fd:
      fd.seek(current_offset, io.SEEK_SET)  # absolute file positioning
      while bytes_left_to_read > 0:

        read_size = min(blob_size, bytes_left_to_read)
        data = fd.read(read_size)

        # Discard data that we read unnecessarily due to alignment.
        # Refer to `_AlignArgs` documentation for more details.
        if is_first_chunk:
          data = data[self._pre_padding:]
          is_first_chunk = False

        # Upload the blobs to blobstore using `TransferStore`. Save the buffer
        # references so we can report it back in the end.
        if data:
          # We need to update the offset as-if it had started from 0 all along,
          # in order to avoid `InvalidBlobOffsetError` when storing the blobs as
          # a file in `file_store`.
          reference_offset = (
              current_offset - self._pre_padding if current_offset else 0)
          self._StoreDataAndHash(data, reference_offset)
        current_offset = current_offset + read_size
        bytes_left_to_read -= read_size

        self.Progress()

  def _StoreDataAndHash(self, data: AnyStr, offset: int) -> None:
    """Uploads data as blob and replies hash to flow.

    Args:
      data: Bytes to be stored as a blob.
      offset: Offset where the data was read from.
    """

    data_blob = rdf_protodict.DataBlob(
        data=zlib.compress(data),
        compression=rdf_protodict.DataBlob.CompressionType.ZCOMPRESSION)

    # Ensure that the buffer is counted against this response. Check network
    # send limit.
    self.ChargeBytesToSession(len(data))

    # Now return the data to the server into the special TransferStore well
    # known flow.
    self.grr_worker.SendReply(
        data_blob, session_id=rdfvalue.SessionID(flow_name="TransferStore"))

    # Now report the hash of this blob to our flow as well as the offset and
    # length.
    digest = hashlib.sha256(data).digest()

    buffer_reference = rdf_client.BufferReference(
        offset=offset, length=len(data), data=digest)
    self._partial_file_hash.update(data)
    partial_file_hash = self._partial_file_hash.digest()

    self.SendReply(
        rdf_read_low_level.ReadLowLevelResult(
            blob=buffer_reference, accumulated_hash=partial_file_hash))


def GetPrePadding(args: rdf_read_low_level.ReadLowLevelRequest) -> int:
  """Calculates the amount of pre_padding to be added when reading data.

  Args:
    args: Original ReadLowLevelRequest sent to this ClientAction.

  Returns:
    The pre padding to be added to the offset (for alignment).
  """

  block_size = args.sector_block_size or _DEFAULT_SECTOR_BLOCK_SIZE
  return args.offset % block_size


def AlignArgs(args: rdf_read_low_level.ReadLowLevelRequest,
              pre_padding: int) -> rdf_read_low_level.ReadLowLevelRequest:
  """Aligns the offset and updates the length according to the pre_padding.

  It returns a copy of the flow arguments with the aligned offset value,
  updated length.

  The alignment means more data than requested can be read.

  From a software architecture point of view, this logic should be
  platform-specific than a shared client action. Thus clients in platforms
  that require the alignment would have this, and others would not. However,
  for simplicity we're going with the same implementation in all platforms.

  - Linux does not require sector alignment for reads.
  - Windows requires sector alignment for raw device access.
  - Mac raw disk devices are not seekable to the end and have no size, so the
    alignment logic helps.

  Args:
    args: Original ReadLowLevelRequest sent to this ClientAction.
    pre_padding: Bytes to remove from the offset and add to the length.

  Returns:
    A copy of the flow args with the aligned offset and length.
  """

  # Due to alignment we will read some more data than we need to.
  aligned_params = args.Copy()
  aligned_params.offset = args.offset - pre_padding
  aligned_params.length = args.length + pre_padding

  return aligned_params
