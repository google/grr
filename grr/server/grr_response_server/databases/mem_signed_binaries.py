#!/usr/bin/env python
"""In-memory implementation of DB methods for handling signed binaries."""

from collections.abc import Sequence
from typing import cast

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_proto import objects_pb2
from grr_response_server.databases import db


def _SignedBinaryKeyFromID(
    binary_id: objects_pb2.SignedBinaryID,
) -> tuple[int, str]:
  """Converts a binary id to an equivalent dict key (tuple)."""
  return int(binary_id.binary_type), binary_id.path


def _SignedBinaryIDFromKey(
    binary_key: tuple[int, str],
) -> objects_pb2.SignedBinaryID:
  """Converts a tuple representing a signed binary to a SignedBinaryID."""
  return objects_pb2.SignedBinaryID(
      # Enums are ints, but generated protobuf annotations do not list
      # int as acceptable argument type.
      binary_type=cast(objects_pb2.SignedBinaryID.BinaryType, binary_key[0]),
      path=binary_key[1],
  )


# TODO(user): Remove this pytype exception when DB mixins are refactored to
# be more self-contained (self.signed_binary_references is not initialized
# in the mixin's __init__ method, as it should be).
# pytype: disable=attribute-error
class InMemoryDBSignedBinariesMixin(object):
  """Mixin providing an in-memory implementation of signed binary DB logic.

  Attributes:
    signed_binary_references: A dict mapping (binary-type, binary-path) tuples
      which uniquely identify signed binaries to (objects_pb2.BlobReferences,
      timestamp) tuples. This field is initialized in mem.py, for consistency
      with other in-memory DB mixins.
  """

  @utils.Synchronized
  def WriteSignedBinaryReferences(
      self,
      binary_id: objects_pb2.SignedBinaryID,
      references: objects_pb2.BlobReferences,
  ):
    """See db.Database."""
    references_copy = objects_pb2.BlobReferences()
    references_copy.CopyFrom(references)

    self.signed_binary_references[_SignedBinaryKeyFromID(binary_id)] = (
        references_copy,
        rdfvalue.RDFDatetime.Now(),
    )

  @utils.Synchronized
  def ReadSignedBinaryReferences(
      self, binary_id: objects_pb2.SignedBinaryID
  ) -> tuple[objects_pb2.BlobReferences, rdfvalue.RDFDatetime]:
    """See db.Database."""
    binary_key = _SignedBinaryKeyFromID(binary_id)
    try:
      references, timestamp = self.signed_binary_references[binary_key]
    except KeyError:
      raise db.UnknownSignedBinaryError(binary_id)

    ref_copy = objects_pb2.BlobReferences()
    ref_copy.CopyFrom(references)
    return ref_copy, timestamp.Copy()

  @utils.Synchronized
  def ReadIDsForAllSignedBinaries(self) -> Sequence[objects_pb2.SignedBinaryID]:
    """See db.Database."""
    return [_SignedBinaryIDFromKey(k) for k in self.signed_binary_references]

  def DeleteSignedBinaryReferences(
      self,
      binary_id: objects_pb2.SignedBinaryID,
  ) -> None:
    """See db.Database."""
    try:
      del self.signed_binary_references[_SignedBinaryKeyFromID(binary_id)]
    except KeyError:
      pass  # Entry doesn't exist, or already deleted; that's ok.


# pytype: enable=attribute-error
