#!/usr/bin/env python
"""The blob store abstraction."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import abc

from future.utils import with_metaclass

from grr_response_core.lib.util import precondition
from grr_response_server.rdfvalues import objects as rdf_objects

# Global blob stores registry.
#
# NOTE: this is a rudimentary registry that will be migrated to the uniform
# registry approach by hanuszczak@ (currently in the works).
REGISTRY = {}


class BlobStore(with_metaclass(abc.ABCMeta, object)):
  """The blob store base class."""

  def WriteBlobsWithUnknownHashes(self, blobs_data):
    """Calculates hash ids and writes contents of given data blobs.

    Args:
      blobs_data: An iterable of bytes.

    Returns:
      A list of rdf_objects.BlobID objects with each blob id corresponding
      to an element in the original blobs_data argument.
    """
    blobs_ids = [rdf_objects.BlobID.FromBlobData(d) for d in blobs_data]
    self.WriteBlobs(dict(zip(blobs_ids, blobs_data)))
    return blobs_ids

  def WriteBlobWithUnknownHash(self, blob_data):
    """Calculates hash id and writes a single gvien blob.

    Args:
      blob_data: Blob contents as bytes.

    Returns:
      rdf_objects.BlobID identifying the blob.
    """
    return self.WriteBlobsWithUnknownHashes([blob_data])[0]

  def ReadBlob(self, blob_id):
    """Reads a blob corresponding to a given hash id.

    Args:
      blob_id: rdf_objects.BlobID object identifying the blob.

    Returns:
      Bytes corresponding to a given blob or None if such blob
      does not exist.
    """
    return self.ReadBlobs([blob_id])[blob_id]

  def CheckBlobExists(self, blob_id):
    """Checks if a blob with a given hash id exists.

    Args:
      blob_id: rdf_objects.BlobID object identifying the blob.

    Returns:
      True if the blob exists, False otherwise.
    """
    return self.CheckBlobsExist([blob_id])[blob_id]

  @abc.abstractmethod
  def WriteBlobs(self, blob_id_data_map):
    """Creates or overwrites blobs.

    Args:
      blob_id_data_map: An dict of blob_id -> blob_datas. Each blob_id should be
        a blob hash (i.e. uniquely idenitify the blob) expressed as
        rdf_objects.BlobID. blob_data should be expressed as bytes.
    """

  @abc.abstractmethod
  def ReadBlobs(self, blob_ids):
    """Reads blobs.

    Args:
      blob_ids: An iterable with blob hashes expressed as bytes.

    Returns:
      A map of {blob_id: blob_data} where blob_data is blob bytes previously
      written with WriteBlobs. If blob_data for particular blob are not found,
      blob_data is expressed as None.
    """

  @abc.abstractmethod
  def CheckBlobsExist(self, blob_ids):
    """Checks if blobs for the given identifiers already exist.

    Args:
      blob_ids: An iterable with blob hashes expressed as bytes.

    Returns:
      A map of {blob_id: status} where status is a boolean (True if blob exists,
      False if it doesn't).
    """


class BlobStoreValidationWrapper(BlobStore):
  """BlobStore wrapper that validates calls arguments."""

  def __init__(self, delegate):
    super(BlobStoreValidationWrapper, self).__init__()
    self.delegate = delegate

  def WriteBlobs(self, blob_id_data_map):
    precondition.AssertDictType(blob_id_data_map, rdf_objects.BlobID, bytes)
    self.delegate.WriteBlobs(blob_id_data_map)

  def ReadBlobs(self, blob_ids):
    precondition.AssertIterableType(blob_ids, rdf_objects.BlobID)

    return self.delegate.ReadBlobs(blob_ids)

  def CheckBlobsExist(self, blob_ids):
    precondition.AssertIterableType(blob_ids, rdf_objects.BlobID)

    return self.delegate.CheckBlobsExist(blob_ids)
