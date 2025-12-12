#!/usr/bin/env python
"""A module with YARA-related methods of the in-memory database."""

from grr_response_proto import objects_pb2
from grr_response_server.databases import db
from grr_response_server.models import blobs as models_blobs


class InMemoryDBYaraMixin(object):
  """An in-memory database mixin with YARA-related methods."""

  def __init__(self):
    super().__init__()
    self.yara: dict[models_blobs.BlobID, str] = {}
    self.users: dict[str, objects_pb2.GRRUser] = {}

  def WriteYaraSignatureReference(
      self,
      blob_id: models_blobs.BlobID,
      username: str,
  ) -> None:
    """Marks specified blob id as a YARA signature."""
    if username not in self.users:
      raise db.UnknownGRRUserError(username=username)

    self.yara[blob_id] = username

  def VerifyYaraSignatureReference(
      self,
      blob_id: models_blobs.BlobID,
  ) -> bool:
    """Verifies whether specified blob is a YARA signature."""
    return blob_id in self.yara
