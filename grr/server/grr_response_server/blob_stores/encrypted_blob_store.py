#!/usr/bin/env python
"""An module with implementation of the encrypted blobstore."""
import logging
from typing import Iterable
from typing import Optional

from grr_response_server import blob_store
from grr_response_server.databases import db as abstract_db
from grr_response_server.keystore import abstract as abstract_ks
from grr_response_server.rdfvalues import objects as rdf_objects


class EncryptedBlobStore(blob_store.BlobStore):
  """An implementation of blobstore that adds an encryption layer to blobs."""

  def __init__(
      self,
      bs: blob_store.BlobStore,
      db: abstract_db.Database,
      ks: abstract_ks.Keystore,
      key_name: str,
  ) -> None:
    """Initializes the encryption-aware blobstore implementation.

    Args:
      bs: A blobstore instance to which encrypted blobs are to be written.
      db: A database used to store encryption key and related metadata.
      ks: A keystore to fetch the keys from.
      key_name: A name of the currently active key to encrypt new blobs with.

    Returns:
      Nothing.
    """
    super().__init__()

    self._bs = bs
    self._db = db
    self._ks = ks
    self._key_name = key_name

  def WriteBlobs(
      self,
      blobs: dict[rdf_objects.BlobID, bytes],
  ) -> None:
    """Writes blobs to the blobstore."""
    crypter = self._ks.Crypter(self._key_name)

    encrypted_blobs = dict()
    key_names = dict()

    for blob_id, blob in blobs.items():
      blob_id_bytes = blob_id.AsBytes()

      encrypted_blobs[blob_id] = crypter.Encrypt(blob, blob_id_bytes)
      key_names[blob_id] = self._key_name

    logging.info("Writing %s encrypted blobs using key '%s' (%s)", len(blobs),
                 self._key_name, ", ".join(map(str, blobs)))

    self._bs.WriteBlobs(encrypted_blobs)
    self._db.WriteBlobEncryptionKeys(key_names)

    logging.info("%s encrypted blobs written", len(blobs))

  def ReadBlobs(
      self,
      blob_ids: Iterable[rdf_objects.BlobID],
  ) -> dict[rdf_objects.BlobID, Optional[bytes]]:
    """Reads specified blobs from the blobstore."""
    blobs = dict()

    key_names = self._db.ReadBlobEncryptionKeys(list(blob_ids))
    encrypted_blobs = self._bs.ReadBlobs(blob_ids)

    for blob_id, encrypted_blob in encrypted_blobs.items():
      if encrypted_blob is None:
        blobs[blob_id] = None
        continue

      blob_id_bytes = blob_id.AsBytes()

      key_name = key_names[blob_id]
      if key_name is None:
        # There is no associated key. It is possible that the blob is just not
        # encrypted: we can verify by computing its blob identifier and compare
        # it with the identifier we wanted to read.
        if rdf_objects.BlobID.FromBlobData(encrypted_blob) == blob_id:
          # The blob identifier of "encrypted" blob matches to blob identifier
          # of the original blob, which means it is not encrypted, and we can
          # just return it.
          blobs[blob_id] = encrypted_blob
        else:
          # This case is more difficult: the blob is encrypted (because the
          # identifiers do not match) but we don't have associated key in the
          # database. This can happen because of a bug or some data loss. But
          # it can also happen because writing blobs and encryption keys is not
          # atomic: they are two separate stores and blobs can be written faster
          # than associated keys in the database.
          #
          # But in this case it means that the write must have happened very,
          # very recently and must have been done with the current key. Thus, we
          # can attempt to decrypt the data with the current key.
          #
          # Note that even with this approach there is a tiny chance of race in
          # case we switch the key between writes to blobstore and database. But
          # this is no worse than server shutting down between the two (not very
          # likely but technically possible) in which case we would end up in
          # inconsistent state anyway.
          crypter = self._ks.Crypter(self._key_name)
          try:
            blob = crypter.Decrypt(encrypted_blob, blob_id_bytes)
          except abstract_ks.DecryptionError:
            raise EncryptedBlobWithoutKeysError(blob_id)  # pylint: disable=raise-missing-from

          blobs[blob_id] = blob

        continue

      # AES GCM that we use guarantees that the data we decrypt was not tampered
      # with (or that we don't try to decrypt some garbage bytes). We use blob
      # identifiers for confirming data authenticity.
      crypter = self._ks.Crypter(key_name)

      blobs[blob_id] = crypter.Decrypt(encrypted_blob, blob_id_bytes)

    return blobs

  def CheckBlobsExist(
      self,
      blob_ids: Iterable[rdf_objects.BlobID],
  ) -> dict[rdf_objects.BlobID, bool]:
    """Checks whether the specified blobs exist in the blobstore."""
    return self._bs.CheckBlobsExist(blob_ids)


class EncryptedBlobWithoutKeysError(Exception):
  """An error for cases when we encounter an encrypted blob without keys.

  This can happen in cases when blob data is written into the blobstore but
  writing the encryption keys to the database fails.
  """

  def __init__(self, blob_id: rdf_objects.BlobID) -> None:
    """Initializes the error.

    Args:
      blob_id: An identifier of a blob that has no associated encryption keys.
    """
    super().__init__(f"Encrypted blob '{blob_id}' with no encryption keys")
    self.blob_id = blob_id
