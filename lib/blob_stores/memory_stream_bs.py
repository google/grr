#!/usr/bin/env python
"""A blob store based on memory stream objects."""

import hashlib

import logging
from grr.lib import aff4
from grr.lib import blob_store
from grr.lib import data_store
from grr.lib import rdfvalue


class MemoryStreamBlobstore(blob_store.Blobstore):
  """A blob store based on memory streams for backwards compatibility."""

  def _BlobUrn(self, digest):
    return rdfvalue.RDFURN("aff4:/blobs").Add(digest)

  def StoreBlobs(self, contents, token=None):
    """Creates or overwrites blobs."""

    instant_sync = len(contents) <= 1
    dirty = False
    res = []
    for content in contents:
      digest = hashlib.sha256(content).hexdigest()
      res.append(digest)
      blob_urn = self._BlobUrn(digest)

      # Historic data may be stored as an AFFMemoryStream, but we store new
      # objects as AFFUnversioned MemoryStreams.
      try:
        fd = aff4.FACTORY.Open(blob_urn,
                               "AFF4MemoryStreamBase",
                               mode="r",
                               token=token)
      except IOError:
        fd = aff4.FACTORY.Create(blob_urn,
                                 "AFF4UnversionedMemoryStream",
                                 mode="w",
                                 token=token)
        fd.Write(content)
        fd.Close(sync=instant_sync)
        dirty = True

      logging.debug("Got blob %s (length %s)", digest, len(content))

    if not instant_sync and dirty:
      data_store.DB.Flush()

    return res

  def ReadBlobs(self, digests, token=None):
    res = {}
    urns = {self._BlobUrn(digest): digest for digest in digests}

    fds = aff4.FACTORY.MultiOpen(urns, mode="r", token=token)
    for fd in fds:
      res[urns[fd.urn]] = fd.read()

    return res

  def BlobsExist(self, digests, token=None):
    """Check if blobs for the given digests already exist."""
    res = {digest: False
           for digest in digests}

    urns = {self._BlobUrn(digest): digest for digest in digests}

    existing = aff4.FACTORY.MultiOpen(
        urns, aff4_type="AFF4MemoryStream", mode="r", token=token)

    for blob in existing:
      res[urns[blob.urn]] = True

    return res
