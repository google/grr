#!/usr/bin/env python
"""The in-memory database methods for blob encryption keys."""
from collections.abc import Collection
from typing import Optional

from grr_response_server.models import blobs as models_blobs


class InMemoryDBBlobKeysMixin:
  """A mixin proving blob encryption key methods for in-memory database."""

  blob_keys: dict[models_blobs.BlobID, str]

  def WriteBlobEncryptionKeys(
      self,
      key_names: dict[models_blobs.BlobID, str],
  ) -> None:
    """Associates the specified blobs with the given encryption keys."""
    self.blob_keys.update(key_names)

  def ReadBlobEncryptionKeys(
      self,
      blob_ids: Collection[models_blobs.BlobID],
  ) -> dict[models_blobs.BlobID, Optional[str]]:
    """Retrieves encryption keys associated with blobs."""
    return dict(zip(blob_ids, map(self.blob_keys.get, blob_ids)))
