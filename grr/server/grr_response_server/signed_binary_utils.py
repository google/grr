#!/usr/bin/env python
# Lint as: python3
"""Utilities for managing signed binaries."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import io


from typing import Iterable, Iterator, Generator, Optional, Sequence, Tuple, Union

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import crypto as rdf_crypto
from grr_response_server import data_store
from grr_response_server.databases import db
from grr_response_server.rdfvalues import objects as rdf_objects


class Error(Exception):
  """Base error class for signed_binary_utils."""


class BlobIndexOutOfBoundsError(Exception):
  """Raised when reading a blob with index > total number of blobs."""


def GetAFF4PythonHackRoot():
  return rdfvalue.RDFURN("aff4:/config/python_hacks")


def GetAFF4ExecutablesRoot():
  return rdfvalue.RDFURN("aff4:/config/executables")


def SignedBinaryIDFromURN(
    binary_urn: rdfvalue.RDFURN) -> rdf_objects.SignedBinaryID:
  """Converts an AFF4 URN for a signed binary to a SignedBinaryID."""
  if binary_urn.RelativeName(GetAFF4PythonHackRoot()):
    return rdf_objects.SignedBinaryID(
        binary_type=rdf_objects.SignedBinaryID.BinaryType.PYTHON_HACK,
        path=binary_urn.RelativeName(GetAFF4PythonHackRoot()))
  elif binary_urn.RelativeName(GetAFF4ExecutablesRoot()):
    return rdf_objects.SignedBinaryID(
        binary_type=rdf_objects.SignedBinaryID.BinaryType.EXECUTABLE,
        path=binary_urn.RelativeName(GetAFF4ExecutablesRoot()))
  else:
    raise ValueError("Unable to determine type of signed binary: %s." %
                     binary_urn)


def _SignedBinaryURNFromID(binary_id: rdf_objects.SignedBinaryID
                          ) -> rdfvalue.RDFURN:
  """Converts a SignedBinaryID to the equivalent AFF4 URN."""
  binary_type = binary_id.binary_type
  if binary_type == rdf_objects.SignedBinaryID.BinaryType.PYTHON_HACK:
    return GetAFF4PythonHackRoot().Add(binary_id.path)
  elif binary_type == rdf_objects.SignedBinaryID.BinaryType.EXECUTABLE:
    return GetAFF4ExecutablesRoot().Add(binary_id.path)
  else:
    raise ValueError("Unknown binary type %s." % binary_type)


class SignedBinaryNotFoundError(Exception):
  """Exception raised when a signed binary is not found in the datastore."""

  def __init__(self, binary_urn):
    super().__init__("Binary with urn %s was not found." % binary_urn)


def WriteSignedBinary(binary_urn: rdfvalue.RDFURN,
                      binary_content: bytes,
                      private_key: rdf_crypto.RSAPrivateKey,
                      public_key: Optional[rdf_crypto.RSAPublicKey],
                      chunk_size: int = 1024):
  """Signs a binary and saves it to the datastore.

  If a signed binary with the given URN already exists, its contents will get
  overwritten.

  Args:
    binary_urn: URN that should serve as a unique identifier for the binary.
    binary_content: Contents of the binary, as raw bytes.
    private_key: Key that should be used for signing the binary contents.
    public_key: Key that should be used to verify the signature generated using
      the private key.
    chunk_size: Size, in bytes, of the individual blobs that the binary contents
      will be split to before saving to the datastore.
  """
  blob_references = rdf_objects.BlobReferences()
  for chunk_offset in range(0, len(binary_content), chunk_size):
    chunk = binary_content[chunk_offset:chunk_offset + chunk_size]
    blob_rdf = rdf_crypto.SignedBlob()
    blob_rdf.Sign(chunk, private_key, verify_key=public_key)
    blob_id = data_store.BLOBS.WriteBlobWithUnknownHash(
        blob_rdf.SerializeToBytes())
    blob_references.items.Append(
        rdf_objects.BlobReference(
            offset=chunk_offset, size=len(chunk), blob_id=blob_id))
  data_store.REL_DB.WriteSignedBinaryReferences(
      SignedBinaryIDFromURN(binary_urn), blob_references)


def WriteSignedBinaryBlobs(binary_urn: rdfvalue.RDFURN,
                           blobs: Iterable[rdf_crypto.SignedBlob]):
  """Saves signed blobs to the datastore.

  If a signed binary with the given URN already exists, its contents will get
  overwritten.

  Args:
    binary_urn: RDFURN that should serve as a unique identifier for the binary.
    blobs: An Iterable of signed blobs to write to the datastore.
  """
  blob_references = rdf_objects.BlobReferences()
  current_offset = 0
  for blob in blobs:
    blob_id = data_store.BLOBS.WriteBlobWithUnknownHash(blob.SerializeToBytes())
    blob_references.items.Append(
        rdf_objects.BlobReference(
            offset=current_offset, size=len(blob.data), blob_id=blob_id))
    current_offset += len(blob.data)
  data_store.REL_DB.WriteSignedBinaryReferences(
      SignedBinaryIDFromURN(binary_urn), blob_references)


def DeleteSignedBinary(binary_urn: rdfvalue.RDFURN):
  """Deletes the binary with the given urn from the datastore.

  Args:
    binary_urn: RDFURN that serves as a unique identifier for the binary.

  Raises:
    SignedBinaryNotFoundError: If the signed binary does not exist.
  """
  try:
    data_store.REL_DB.ReadSignedBinaryReferences(
        SignedBinaryIDFromURN(binary_urn))
  except db.UnknownSignedBinaryError:
    raise SignedBinaryNotFoundError(binary_urn)
  data_store.REL_DB.DeleteSignedBinaryReferences(
      SignedBinaryIDFromURN(binary_urn))


def FetchURNsForAllSignedBinaries() -> Sequence[rdfvalue.RDFURN]:
  """Returns URNs for all signed binaries in the datastore."""
  return [
      _SignedBinaryURNFromID(i)
      for i in data_store.REL_DB.ReadIDsForAllSignedBinaries()
  ]


def FetchBlobsForSignedBinaryByID(
    binary_id: rdf_objects.SignedBinaryID
) -> Tuple[Iterator[rdf_crypto.SignedBlob], rdfvalue.RDFDatetime]:
  """Retrieves blobs for the given binary from the datastore.

  Args:
    binary_id: An ID of the binary to be fetched.

  Returns:
    A tuple containing an iterator for all the binary's blobs and an
    RDFDatetime representing when the binary's contents were saved
    to the datastore.

  Raises:
    SignedBinaryNotFoundError: If no signed binary with the given URN exists.
  """
  try:
    references, timestamp = data_store.REL_DB.ReadSignedBinaryReferences(
        binary_id)
  except db.UnknownSignedBinaryError:
    raise SignedBinaryNotFoundError(_SignedBinaryURNFromID(binary_id))
  blob_ids = [r.blob_id for r in references.items]
  raw_blobs = (data_store.BLOBS.ReadBlob(blob_id) for blob_id in blob_ids)
  blobs = (
      rdf_crypto.SignedBlob.FromSerializedBytes(raw_blob)
      for raw_blob in raw_blobs)
  return blobs, timestamp


def FetchBlobForSignedBinaryByID(
    binary_id: rdf_objects.SignedBinaryID,
    blob_index: int,
) -> rdf_crypto.SignedBlob:
  """Retrieves a single blob for the given binary from the datastore.

  Args:
    binary_id: An ID of the binary to be fetched.
    blob_index: Index of the blob to read.

  Returns:
    Signed blob.

  Raises:
    SignedBinaryNotFoundError: If no signed binary with the given URN exists.
    BlobIndexOutOfBoundsError: If requested blob index is too big.
  """
  if blob_index < 0:
    raise ValueError("blob_index must be >= 0.")

  try:
    references, _ = data_store.REL_DB.ReadSignedBinaryReferences(binary_id)
  except db.UnknownSignedBinaryError:
    raise SignedBinaryNotFoundError(_SignedBinaryURNFromID(binary_id))

  try:
    blob_id = references.items[blob_index].blob_id
  except IndexError:
    raise BlobIndexOutOfBoundsError(f"{blob_index} >= {len(references.items)}")

  raw_blob = data_store.BLOBS.ReadBlob(blob_id)
  return rdf_crypto.SignedBlob.FromSerializedBytes(raw_blob)


def FetchBlobsForSignedBinaryByURN(
    binary_urn: rdfvalue.RDFURN
) -> Tuple[Iterator[rdf_crypto.SignedBlob], rdfvalue.RDFDatetime]:
  """Retrieves blobs for the given binary from the datastore.

  Args:
    binary_urn: RDFURN that uniquely identifies the binary.

  Returns:
    A tuple containing an iterator for all the binary's blobs and an
    RDFDatetime representing when the binary's contents were saved
    to the datastore.

  Raises:
    SignedBinaryNotFoundError: If no signed binary with the given URN exists.
  """
  return FetchBlobsForSignedBinaryByID(SignedBinaryIDFromURN(binary_urn))


def FetchBlobForSignedBinaryByURN(
    binary_urn: rdfvalue.RDFURN,
    blob_index: int,
) -> rdf_crypto.SignedBlob:
  """Retrieves blobs for the given binary from the datastore.

  Args:
    binary_urn: RDFURN that uniquely identifies the binary.
    blob_index: Index of the blob to read.

  Returns:
    Signed blob.

  Raises:
    SignedBinaryNotFoundError: If no signed binary with the given URN exists.
    BlobIndexOutOfBoundsError: If requested blob index is too big.
  """
  return FetchBlobForSignedBinaryByID(
      SignedBinaryIDFromURN(binary_urn), blob_index)


def FetchSizeOfSignedBinary(
    binary_id_or_urn: Union[rdf_objects.SignedBinaryID,
                            rdfvalue.RDFURN]) -> int:
  """Returns the size of the given binary (in bytes).

  Args:
    binary_id_or_urn: SignedBinaryID or RDFURN that uniquely identifies the
        binary.

  Raises:
    SignedBinaryNotFoundError: If no signed binary with the given URN exists.
  """
  if isinstance(binary_id_or_urn, rdfvalue.RDFURN):
    binary_id = SignedBinaryIDFromURN(binary_id_or_urn)
  else:
    binary_id = binary_id_or_urn
  try:
    references, _ = data_store.REL_DB.ReadSignedBinaryReferences(binary_id)
  except db.UnknownSignedBinaryError:
    raise SignedBinaryNotFoundError(binary_id)
  last_reference = references.items[-1]
  return last_reference.offset + last_reference.size


def StreamSignedBinaryContents(blob_iterator: Iterator[rdf_crypto.SignedBlob],
                               chunk_size: int = 1024
                              ) -> Generator[bytes, None, None]:
  """Yields the contents of the given binary in chunks of the given size.

  Args:
    blob_iterator: An Iterator over all the binary's blobs.
    chunk_size: Size, in bytes, of the chunks to yield.
  """
  all_blobs_read = False
  byte_buffer = io.BytesIO()
  while not all_blobs_read or byte_buffer.getvalue():
    while not all_blobs_read and byte_buffer.tell() < chunk_size:
      try:
        blob = next(blob_iterator)
      except StopIteration:
        all_blobs_read = True
        break
      byte_buffer.write(blob.data)
    if byte_buffer.tell() > 0:
      # Yield a chunk of the signed binary and reset the buffer to contain
      # only data that hasn't been sent yet.
      byte_buffer.seek(0)
      yield byte_buffer.read(chunk_size)
      byte_buffer = io.BytesIO(byte_buffer.read())
      byte_buffer.seek(0, io.SEEK_END)
