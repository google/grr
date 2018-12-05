#!/usr/bin/env python
"""Utility classes for uploading files to the server."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import hashlib
import zlib

from grr_response_client import streaming
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict


class TransferStoreUploader(object):
  """An utility class for uploading chunked files to the server.

  Input is divided into chunks, then these chunks are compressed (using zlib)
  and then they are uploaded to the transfer store (a well-known flow).
  """

  DEFAULT_CHUNK_SIZE = 512 * 1024

  _TRANSFER_STORE_SESSION_ID = rdfvalue.SessionID(flow_name="TransferStore")

  def __init__(self, action, chunk_size=None):
    """Initializes the uploader.

    Args:
      action: A parent action that creates the uploader. Used to communicate
              with the parent flow.
      chunk_size: A number of (uncompressed) bytes per a chunk.
    """
    chunk_size = chunk_size or self.DEFAULT_CHUNK_SIZE

    self._action = action
    self._streamer = streaming.Streamer(chunk_size=chunk_size)

  def UploadFilePath(self, filepath, offset=0, amount=None):
    """Uploads chunks of a file on a given path to the transfer store flow.

    Args:
      filepath: A path to the file to upload.
      offset: An integer offset at which the file upload should start on.
      amount: An upper bound on number of bytes to stream. If it is `None` then
          the whole file is uploaded.

    Returns:
      A `BlobImageDescriptor` object.
    """
    chunk_stream = self._streamer.StreamFilePath(
        filepath, offset=offset, amount=amount)

    chunks = []
    for chunk in chunk_stream:
      chunks.append(self.UploadChunk(chunk))

    return rdf_client_fs.BlobImageDescriptor(
        chunks=chunks, chunk_size=self._streamer.chunk_size)

  def UploadChunk(self, chunk):
    """Uploads a single chunk to the transfer store flow.

    Args:
      chunk: A chunk to upload.

    Returns:
      A `BlobImageChunkDescriptor` object.
    """
    blob = _CompressedDataBlob(chunk)

    self._action.ChargeBytesToSession(len(chunk.data))
    self._action.SendReply(blob, session_id=self._TRANSFER_STORE_SESSION_ID)

    return rdf_client_fs.BlobImageChunkDescriptor(
        digest=hashlib.sha256(chunk.data).digest(),
        offset=chunk.offset,
        length=len(chunk.data))


def _CompressedDataBlob(chunk):
  return rdf_protodict.DataBlob(
      data=zlib.compress(chunk.data),
      compression=rdf_protodict.DataBlob.CompressionType.ZCOMPRESSION)
