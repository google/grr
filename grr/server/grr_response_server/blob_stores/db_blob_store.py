#!/usr/bin/env python
"""REL_DB blobstore implementation."""
from typing import Dict
from typing import Iterable
from typing import Optional

from grr_response_server import blob_store
from grr_response_server import data_store
from grr_response_server.rdfvalues import objects as rdf_objects


class DbBlobStore(blob_store.BlobStore):
  """A REL_DB-based blob store implementation."""

  def __init__(self, delegate: Optional[blob_store.BlobStore] = None) -> None:
    """Initializes the database-backed blobstore.

    Args:
      delegate: A database to use for the blobstore. If none is provided, the
        global relational database object is used.
    """
    if delegate is None:
      # The global database object is the validation wrapper, so we need to take
      # its delegate (as the validation wrapper does not implement the blobstore
      # interface).
      delegate = data_store.REL_DB.delegate  # pytype: disable=attribute-error
      if not isinstance(delegate, blob_store.BlobStore):
        raise TypeError(f"Database blobstore delegate of '{type(delegate)}' "
                        f"type does not implement the blobstore interface")

    self._delegate = delegate

  def WriteBlobs(
      self,
      blob_id_data_map: Dict[rdf_objects.BlobID, bytes],
  ) -> None:
    return self._delegate.WriteBlobs(blob_id_data_map)

  def ReadBlobs(
      self,
      blob_ids: Iterable[rdf_objects.BlobID],
  ) -> Dict[rdf_objects.BlobID, Optional[bytes]]:
    return self._delegate.ReadBlobs(blob_ids)

  def CheckBlobsExist(
      self,
      blob_ids: Iterable[rdf_objects.BlobID],
  ) -> Dict[rdf_objects.BlobID, bool]:
    return self._delegate.CheckBlobsExist(blob_ids)
