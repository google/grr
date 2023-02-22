#!/usr/bin/env python
"""A module with YARA-related methods of the in-memory database."""

from typing import Dict
from typing import Text

from grr_response_server.databases import db
from grr_response_server.rdfvalues import objects as rdf_objects


class InMemoryDBYaraMixin(object):
  """An in-memory database mixin with YARA-related methods."""

  def __init__(self):
    super().__init__()
    self.yara: Dict[bytes, Text] = {}
    self.users: Dict[Text, rdf_objects.GRRUser] = {}

  def WriteYaraSignatureReference(
      self,
      blob_id: rdf_objects.BlobID,
      username: Text,
  ) -> None:
    """Marks specified blob id as a YARA signature."""
    if username not in self.users:
      raise db.UnknownGRRUserError(username=username)

    self.yara[blob_id] = username  # pytype: disable=container-type-mismatch

  def VerifyYaraSignatureReference(
      self,
      blob_id: rdf_objects.BlobID,
  ) -> bool:
    """Verifies whether specified blob is a YARA signature."""
    return blob_id in self.yara
