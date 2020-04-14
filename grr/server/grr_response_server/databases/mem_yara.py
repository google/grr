#!/usr/bin/env python
# Lint as: python3
"""A module with YARA-related methods of the in-memory database."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from typing import Dict
from typing import Text

from grr_response_server.databases import db
from grr_response_server.rdfvalues import objects as rdf_objects


class InMemoryDBYaraMixin(object):
  """An in-memory database mixin with YARA-related methods."""

  def __init__(self):
    super().__init__()
    self.yara = {}  # type: Dict[bytes, Text]
    self.users = {}  # type: Dict[Text, rdf_objects.GRRUser]

  def WriteYaraSignatureReference(
      self,
      blob_id: rdf_objects.BlobID,
      username: Text,
  ) -> None:
    """Marks specified blob id as a YARA signature."""
    if username not in self.users:
      raise db.UnknownGRRUserError(username=username)

    self.yara[blob_id] = username

  def VerifyYaraSignatureReference(
      self,
      blob_id: rdf_objects.BlobID,
  ) -> bool:
    """Verifies whether specified blob is a YARA signature."""
    return blob_id in self.yara
