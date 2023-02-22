#!/usr/bin/env python
"""The in-memory database methods for blob encryption keys."""
from typing import Collection
from typing import Dict
from typing import Optional

from grr_response_server.rdfvalues import objects as rdf_objects


class InMemoryDBBlobKeysMixin:
  """A mixin proving blob encryption key methods for in-memory database."""
  blob_keys: Dict[rdf_objects.BlobID, str]

  def WriteBlobEncryptionKeys(
      self,
      key_names: Dict[rdf_objects.BlobID, str],
  ) -> None:
    """Associates the specified blobs with the given encryption keys."""
    self.blob_keys.update(key_names)

  def ReadBlobEncryptionKeys(
      self,
      blob_ids: Collection[rdf_objects.BlobID],
  ) -> Dict[rdf_objects.BlobID, Optional[str]]:
    """Retrieves encryption keys associated with blobs."""
    return dict(zip(blob_ids, map(self.blob_keys.get, blob_ids)))
