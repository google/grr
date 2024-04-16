#!/usr/bin/env python
"""Module with data models and helpers related to blobs."""

import binascii
import hashlib


class BlobID:
  """Unique identifier of a blob store data."""

  def __init__(self, sha256: bytes):
    """Initialize the blob identifier.

    Args:
      sha256: A SHA-256 data digest of the corresponding blob.
    """
    if len(sha256) != 32:
      raise ValueError(f"Incorrect length of blob identifier: {len(sha256)}")

    self._sha256 = sha256

  def __eq__(self, other: "BlobID") -> bool:
    return self._sha256 == other._sha256

  def __bytes__(self) -> bytes:
    return self._sha256

  def __str__(self) -> str:
    return f"BlobID({binascii.hexlify(self._sha256).decode('utf-8')})"

  def __repr__(self) -> str:
    return f"BlobID({self._sha256!r})"

  def __hash__(self) -> int:
    return hash(self._sha256)

  @classmethod
  def Of(cls, blob: bytes) -> "BlobID":
    """Returns identifier of the given blob."""
    return BlobID(hashlib.sha256(blob).digest())
