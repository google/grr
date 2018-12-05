#!/usr/bin/env python
"""Utilities for managing signed binaries."""
from __future__ import absolute_import
from __future__ import division

from __future__ import unicode_literals

import io

from future.builtins import int

from typing import Iterable, Iterator, Generator, Optional, Sequence, Tuple

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import crypto as rdf_crypto
from grr_response_server import access_control
from grr_response_server import aff4
from grr_response_server import data_store
from grr_response_server import db
from grr_response_server.aff4_objects import collects
from grr_response_server.rdfvalues import objects as rdf_objects


def GetAFF4PythonHackRoot():
  return rdfvalue.RDFURN("aff4:/config/python_hacks")


def GetAFF4ExecutablesRoot():
  return rdfvalue.RDFURN("aff4:/config/executables")


def _SignedBinaryIDFromURN(
    binary_urn):
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
    raise ValueError(
        "Unable to determine type of signed binary: %s." % binary_urn)


def _SignedBinaryURNFromID(
    binary_id):
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
    super(SignedBinaryNotFoundError,
          self).__init__("Binary with urn %s was not found." % binary_urn)


def WriteSignedBinary(binary_urn,
                      binary_content,
                      private_key,
                      public_key,
                      chunk_size = 1024,
                      token = None):
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
    token: ACL token to use with the legacy (non-relational) datastore.
  """
  if _ShouldUseLegacyDatastore():
    collects.GRRSignedBlob.NewFromContent(
        binary_content,
        binary_urn,
        chunk_size=chunk_size,
        token=token,
        private_key=private_key,
        public_key=public_key)

  if data_store.RelationalDBWriteEnabled():
    blob_references = rdf_objects.BlobReferences()
    for chunk_offset in range(0, len(binary_content), chunk_size):
      chunk = binary_content[chunk_offset:chunk_offset + chunk_size]
      blob_rdf = rdf_crypto.SignedBlob()
      blob_rdf.Sign(chunk, private_key, verify_key=public_key)
      blob_id = data_store.BLOBS.WriteBlobWithUnknownHash(
          blob_rdf.SerializeToString())
      blob_references.items.Append(
          rdf_objects.BlobReference(
              offset=chunk_offset, size=len(chunk), blob_id=blob_id))
    data_store.REL_DB.WriteSignedBinaryReferences(
        _SignedBinaryIDFromURN(binary_urn), blob_references)


def WriteSignedBinaryBlobs(binary_urn,
                           blobs,
                           token = None):
  """Saves signed blobs to the datastore.

  If a signed binary with the given URN already exists, its contents will get
  overwritten.

  Args:
    binary_urn: RDFURN that should serve as a unique identifier for the binary.
    blobs: An Iterable of signed blobs to write to the datastore.
    token: ACL token to use with the legacy (non-relational) datastore.
  """
  if _ShouldUseLegacyDatastore():
    aff4.FACTORY.Delete(binary_urn, token=token)
    with data_store.DB.GetMutationPool() as mutation_pool:
      with aff4.FACTORY.Create(
          binary_urn,
          collects.GRRSignedBlob,
          mode="w",
          mutation_pool=mutation_pool,
          token=token) as fd:
        for blob in blobs:
          fd.Add(blob, mutation_pool=mutation_pool)

  if data_store.RelationalDBWriteEnabled():
    blob_references = rdf_objects.BlobReferences()
    current_offset = 0
    for blob in blobs:
      blob_id = data_store.BLOBS.WriteBlobWithUnknownHash(
          blob.SerializeToString())
      blob_references.items.Append(
          rdf_objects.BlobReference(
              offset=current_offset, size=len(blob.data), blob_id=blob_id))
      current_offset += len(blob.data)
    data_store.REL_DB.WriteSignedBinaryReferences(
        _SignedBinaryIDFromURN(binary_urn), blob_references)


def DeleteSignedBinary(binary_urn,
                       token = None):
  """Deletes the binary with the given urn from the datastore.

  Args:
    binary_urn: RDFURN that serves as a unique identifier for the binary.
    token: ACL token to use with the legacy (non-relational) datastore.

  Raises:
    SignedBinaryNotFoundError: If the signed binary does not exist.
  """
  if _ShouldUseLegacyDatastore():
    try:
      aff4.FACTORY.Open(
          binary_urn, aff4_type=aff4.AFF4Stream, mode="r", token=token)
    except aff4.InstantiationError:
      raise SignedBinaryNotFoundError(binary_urn)
    aff4.FACTORY.Delete(binary_urn, token=token)

  if data_store.RelationalDBWriteEnabled():
    try:
      data_store.REL_DB.ReadSignedBinaryReferences(
          _SignedBinaryIDFromURN(binary_urn))
    except db.UnknownSignedBinaryError:
      if _ShouldUseLegacyDatastore():
        # Migration of data isn't complete yet (we haven't started reading
        # exclusively from the relational DB), so this is probably ok.
        return
      else:
        raise SignedBinaryNotFoundError(binary_urn)
    data_store.REL_DB.DeleteSignedBinaryReferences(
        _SignedBinaryIDFromURN(binary_urn))


def FetchURNsForAllSignedBinaries(
    token):
  """Returns URNs for all signed binaries in the datastore.

  Args:
    token: ACL token to use with the legacy (non-relational) datastore.
  """
  if _ShouldUseLegacyDatastore():
    urns = []
    aff4_roots = [GetAFF4PythonHackRoot(), GetAFF4ExecutablesRoot()]
    for _, descendant_urns in aff4.FACTORY.RecursiveMultiListChildren(
        aff4_roots):
      urns.extend(descendant_urns)
    aff4_streams = aff4.FACTORY.MultiOpen(
        urns, aff4_type=collects.GRRSignedBlob, mode="r", token=token)
    return [stream.urn for stream in aff4_streams]
  else:
    return [
        _SignedBinaryURNFromID(i)
        for i in data_store.REL_DB.ReadIDsForAllSignedBinaries()
    ]


def FetchBlobsForSignedBinary(
    binary_urn,
    token = None
):
  """Retrieves blobs for the given binary from the datastore.

  Args:
    binary_urn: RDFURN that uniquely identifies the binary.
    token: ACL token to use with the legacy (non-relational) datastore.

  Returns:
    A tuple containing an iterator for all the binary's blobs and an
    RDFDatetime representing when the binary's contents were saved
    to the datastore.

  Raises:
    SignedBinaryNotFoundError: If no signed binary with the given URN exists.
  """
  if _ShouldUseLegacyDatastore():
    try:
      aff4_stream = aff4.FACTORY.Open(
          binary_urn, aff4_type=collects.GRRSignedBlob, mode="r", token=token)
    except aff4.InstantiationError:
      raise SignedBinaryNotFoundError(binary_urn)
    timestamp = aff4_stream.Get(aff4_stream.Schema.TYPE).age
    return (blob for blob in aff4_stream), timestamp
  else:
    try:
      references, timestamp = data_store.REL_DB.ReadSignedBinaryReferences(
          _SignedBinaryIDFromURN(binary_urn))
    except db.UnknownSignedBinaryError:
      raise SignedBinaryNotFoundError(binary_urn)
    blob_ids = [r.blob_id for r in references.items]
    raw_blobs = (data_store.BLOBS.ReadBlob(blob_id) for blob_id in blob_ids)
    blobs = (
        rdf_crypto.SignedBlob.FromSerializedString(raw_blob)
        for raw_blob in raw_blobs)
    return blobs, timestamp


def FetchSizeOfSignedBinary(
    binary_urn,
    token = None):
  """Returns the size of the given binary (in bytes).

  Args:
    binary_urn: RDFURN that uniquely identifies the binary.
    token: ACL token to use with the legacy (non-relational) datastore.

  Raises:
    SignedBinaryNotFoundError: If no signed binary with the given URN exists.
  """
  if _ShouldUseLegacyDatastore():
    try:
      aff4_stream = aff4.FACTORY.Open(
          binary_urn, aff4_type=collects.GRRSignedBlob, mode="r", token=token)
      return aff4_stream.size
    except aff4.InstantiationError:
      raise SignedBinaryNotFoundError(binary_urn)
  else:
    try:
      references, _ = data_store.REL_DB.ReadSignedBinaryReferences(
          _SignedBinaryIDFromURN(binary_urn))
    except db.UnknownSignedBinaryError:
      raise SignedBinaryNotFoundError(binary_urn)
    last_reference = references.items[-1]
    return last_reference.offset + last_reference.size


def StreamSignedBinaryContents(blob_iterator,
                               chunk_size = 1024
                              ):
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


def _ShouldUseLegacyDatastore():
  """Returns a boolean indicating whether we should use the legacy datastore.

  If a relational DB implementation is available, binaries will get saved to
  the relational DB, in addition to the legacy DB. However, we will still be
  reading from the legacy DB until a config option specific to signed binaries
  is enabled. When that happens, we will also stop writing to the legacy DB.
  """
  return not data_store.RelationalDBReadEnabled(category="signed_binaries")
