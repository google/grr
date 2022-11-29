#!/usr/bin/env python
"""The in-memory database methods for blob encryption keys."""
from typing import Collection
from typing import Dict
from typing import Optional

from grr_response_server.databases import db as abstract_db
from grr_response_server.rdfvalues import objects as rdf_objects


class InMemoryDBBlobKeysMixin:
  """A mixin proving blob encryption key methods for in-memory database."""
  blob_keys: Dict[rdf_objects.BlobID, abstract_db.EncryptionKey]

  def WriteBlobEncryptionKeys(
      self,
      keys: Dict[rdf_objects.BlobID, abstract_db.EncryptionKey],
  ) -> None:
    """Associates the specified blobs with the given encryption keys."""
    self.blob_keys.update(keys)

  def ReadBlobEncryptionKeys(
      self,
      blob_ids: Collection[rdf_objects.BlobID],
  ) -> Dict[rdf_objects.BlobID, Optional[abstract_db.EncryptionKey]]:
    """Retrieves encryption keys associated with blobs."""
    return dict(zip(blob_ids, map(self.blob_keys.get, blob_ids)))
