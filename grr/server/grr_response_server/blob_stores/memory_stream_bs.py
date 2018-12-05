#!/usr/bin/env python
"""A blob store based on memory stream objects."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import logging


from future.utils import iteritems

from grr_response_core.lib import rdfvalue
from grr_response_server import aff4
from grr_response_server import blob_store
from grr_response_server import data_store


class MemoryStreamBlobStore(blob_store.BlobStore):
  """A blob store based on memory streams for backwards compatibility."""

  def _BlobUrn(self, blob_id):
    return rdfvalue.RDFURN("aff4:/blobs").Add(blob_id.AsHexString())

  def WriteBlobs(self, blob_id_data_map):
    """Creates or overwrites blobs."""

    urns = {self._BlobUrn(blob_id): blob_id for blob_id in blob_id_data_map}

    mutation_pool = data_store.DB.GetMutationPool()

    existing = aff4.FACTORY.MultiOpen(
        urns, aff4_type=aff4.AFF4MemoryStreamBase, mode="r")

    for blob_urn, blob_id in iteritems(urns):
      if blob_urn in existing:
        logging.debug("Blob %s already stored.", blob_id)
        continue

      with aff4.FACTORY.Create(
          blob_urn,
          aff4.AFF4UnversionedMemoryStream,
          mode="w",
          mutation_pool=mutation_pool) as fd:
        content = blob_id_data_map[blob_id]
        fd.Write(content)

      logging.debug("Got blob %s (length %s)", blob_id.AsHexString(),
                    len(content))

    mutation_pool.Flush()

  def ReadBlobs(self, blob_ids):
    res = {blob_id: None for blob_id in blob_ids}
    urns = {self._BlobUrn(blob_id): blob_id for blob_id in blob_ids}

    fds = aff4.FACTORY.MultiOpen(urns, mode="r")

    for fd in fds:
      res[urns[fd.urn]] = fd.read()

    return res

  def CheckBlobsExist(self, blob_ids):
    """Check if blobs for the given digests already exist."""
    res = {blob_id: False for blob_id in blob_ids}

    urns = {self._BlobUrn(blob_id): blob_id for blob_id in blob_ids}

    existing = aff4.FACTORY.MultiOpen(
        urns, aff4_type=aff4.AFF4MemoryStreamBase, mode="r")

    for blob in existing:
      res[urns[blob.urn]] = True

    return res
