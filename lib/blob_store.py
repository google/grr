#!/usr/bin/env python
"""The blob store abstraction."""

from grr.lib import registry


class Blobstore(object):
  """The blob store base class."""

  __metaclass__ = registry.MetaclassRegistry

  def StoreBlob(self, content, token=None):
    return self.StoreBlobs([content], token=token)[0]

  def ReadBlob(self, digest, token=None):
    return self.ReadBlobs([digest], token=token).values()[0]

  def BlobExists(self, digest, token=None):
    return self.BlobsExist([digest], token=token).values()[0]

  def StoreBlobs(self, contents, token=None):
    """Creates or overwrites blobs.

    Args:
      contents: A list containing data for each blob to be stored.
      token: Data store token.

    Returns:
      A list of hexdigests, one for each stored blob.
    """

  def ReadBlobs(self, digests, token=None):
    """Reads blobs.

    Args:
      digests: A list of digests for the blobs to retrieve.
      token: Data store token.

    Returns:
      A dict mapping each digest to the contents of this blob as a string.
    """

  def BlobsExist(self, digests, token=None):
    """Checks if blobs for the given digests already exist.

    Args:
      digests: A list of digests for the blobs to check.
      token: Data store token.

    Returns:
      A dict mapping each digest to a boolean value indicating existence.
    """
