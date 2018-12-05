#!/usr/bin/env python
"""In-memory implementation of DB methods for handling signed binaries."""
from __future__ import absolute_import
from __future__ import division

from __future__ import unicode_literals

from future.builtins import int
from typing import Sequence, Text, Tuple

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_server import db
from grr_response_server.rdfvalues import objects as rdf_objects


def _SignedBinaryKeyFromID(
    binary_id):
  """Converts a binary id to an equivalent dict key (tuple)."""
  return binary_id.binary_type.SerializeToDataStore(), binary_id.path


def _SignedBinaryIDFromKey(
    binary_key):
  """Converts a tuple representing a signed binary to a SignedBinaryID."""
  return rdf_objects.SignedBinaryID(
      binary_type=binary_key[0], path=binary_key[1])


# TODO(user): Remove this pytype exception when DB mixins are refactored to
# be more self-contained (self.signed_binary_references is not initialized
# in the mixin's __init__ method, as it should be).
# pytype: disable=attribute-error
class InMemoryDBSignedBinariesMixin(object):
  """Mixin providing an in-memory implementation of signed binary DB logic.

  Attributes:
    signed_binary_references: A dict mapping (binary-type, binary-path) tuples
      which uniquely identify signed binaries to (rdf_objects.BlobReferences,
      timestamp) tuples. This field is initialized in mem.py, for consistency
      with other in-memory DB mixins.
  """

  @utils.Synchronized
  def WriteSignedBinaryReferences(self, binary_id,
                                  references):
    """See db.Database."""
    self.signed_binary_references[_SignedBinaryKeyFromID(binary_id)] = (
        references.Copy(), rdfvalue.RDFDatetime.Now())

  @utils.Synchronized
  def ReadSignedBinaryReferences(
      self, binary_id
  ):
    """See db.Database."""
    binary_key = _SignedBinaryKeyFromID(binary_id)
    try:
      references, timestamp = self.signed_binary_references[binary_key]
    except KeyError:
      raise db.UnknownSignedBinaryError(binary_id)
    return references.Copy(), timestamp.Copy()

  @utils.Synchronized
  def ReadIDsForAllSignedBinaries(self):
    """See db.Database."""
    return [_SignedBinaryIDFromKey(k) for k in self.signed_binary_references]

  def DeleteSignedBinaryReferences(self, binary_id):
    """See db.Database."""
    try:
      del self.signed_binary_references[_SignedBinaryKeyFromID(binary_id)]
    except KeyError:
      pass  # Entry doesn't exist, or already deleted; that's ok.


# pytype: enable=attribute-error
