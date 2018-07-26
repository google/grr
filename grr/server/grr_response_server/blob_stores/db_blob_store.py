#!/usr/bin/env python
"""REL_DB blobstore implementation."""

import hashlib

from future.utils import iteritems

from grr_response_server import blob_store
from grr_response_server import data_store
from grr_response_server.rdfvalues import objects as rdf_objects


class DbBlobstore(blob_store.Blobstore):
  """A REL_DB-based blob store implementation."""

  def StoreBlobs(self, contents, token=None):
    """Creates or overwrites blobs."""
    del token  # Unused.

    contents_by_digest = {
        rdf_objects.BlobID(hashlib.sha256(content).digest()): content
        for content in contents
    }

    data_store.REL_DB.WriteBlobs(contents_by_digest)

    return [x.AsBytes().encode("hex") for x in contents_by_digest]

  def ReadBlobs(self, digests, token=None):
    del token  # Unused.

    results = data_store.REL_DB.ReadBlobs(
        [rdf_objects.BlobID(d.decode("hex")) for d in digests])
    return {k.AsBytes().encode("hex"): v for k, v in iteritems(results)}

  def BlobsExist(self, digests, token=None):
    """Check if blobs for the given digests already exist."""
    del token  # Unused.

    results = data_store.REL_DB.CheckBlobsExist(
        [rdf_objects.BlobID(d.decode("hex")) for d in digests])
    return {k.AsBytes().encode("hex"): v for k, v in iteritems(results)}
