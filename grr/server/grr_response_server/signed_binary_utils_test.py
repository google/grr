#!/usr/bin/env python
# Lint as: python3
"""Tests for signed binary utilities."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import collections

from absl import app
from absl.testing import absltest

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import crypto as rdf_crypto
from grr_response_server import signed_binary_utils
from grr_response_server.rdfvalues import objects as rdf_objects
from grr.test_lib import test_lib


class SignedBinaryIDFromURNTest(absltest.TestCase):

  def testCorrectlyConvertsPythonHackURN(self):
    self.assertEqual(
        signed_binary_utils.SignedBinaryIDFromURN(
            rdfvalue.RDFURN("aff4:/config/python_hacks/foo")),
        rdf_objects.SignedBinaryID(
            binary_type=rdf_objects.SignedBinaryID.BinaryType.PYTHON_HACK,
            path="foo"))

  def testCorrectlyConvertsExecutableURN(self):
    self.assertEqual(
        signed_binary_utils.SignedBinaryIDFromURN(
            rdfvalue.RDFURN("aff4:/config/executables/foo")),
        rdf_objects.SignedBinaryID(
            binary_type=rdf_objects.SignedBinaryID.BinaryType.EXECUTABLE,
            path="foo"))

  def testRaisesWhenNeitherPythonHackNorExecutableURNIsPassed(self):
    with self.assertRaises(ValueError):
      signed_binary_utils.SignedBinaryIDFromURN(
          rdfvalue.RDFURN("aff4:/foo/bar"))


class SignedBinaryUtilsTest(test_lib.GRRBaseTest):

  def setUp(self):
    super(SignedBinaryUtilsTest, self).setUp()

    self._private_key = rdf_crypto.RSAPrivateKey.GenerateKey(bits=2048)
    self._public_key = self._private_key.GetPublicKey()

  def testWriteSignedBinary(self):
    binary_data = b"\x00\x11\x22\x33\x44\x55\x66\x77\x88\x99"  # 10 bytes.
    test_urn = rdfvalue.RDFURN("aff4:/config/executables/foo")
    signed_binary_utils.WriteSignedBinary(
        test_urn,
        binary_data,
        private_key=self._private_key,
        public_key=self._public_key,
        chunk_size=3)
    blobs_iter, timestamp = signed_binary_utils.FetchBlobsForSignedBinaryByURN(
        test_urn)
    self.assertGreater(timestamp.AsMicrosecondsSinceEpoch(), 0)
    self.assertIsInstance(blobs_iter, collections.Iterator)
    # We expect blobs to have at most 3 contiguous bytes of data.
    expected_blobs = [
        rdf_crypto.SignedBlob().Sign(b"\x00\x11\x22", self._private_key),
        rdf_crypto.SignedBlob().Sign(b"\x33\x44\x55", self._private_key),
        rdf_crypto.SignedBlob().Sign(b"\x66\x77\x88", self._private_key),
        rdf_crypto.SignedBlob().Sign(b"\x99", self._private_key)
    ]
    self.assertCountEqual(list(blobs_iter), expected_blobs)

  def testWriteSignedBinaryBlobs(self):
    test_urn = rdfvalue.RDFURN("aff4:/config/executables/foo")
    test_blobs = [
        rdf_crypto.SignedBlob().Sign(b"\x00\x11\x22", self._private_key),
        rdf_crypto.SignedBlob().Sign(b"\x33\x44\x55", self._private_key),
        rdf_crypto.SignedBlob().Sign(b"\x66\x77\x88", self._private_key),
        rdf_crypto.SignedBlob().Sign(b"\x99", self._private_key)
    ]
    signed_binary_utils.WriteSignedBinaryBlobs(test_urn, test_blobs)
    blobs_iter, timestamp = signed_binary_utils.FetchBlobsForSignedBinaryByURN(
        test_urn)
    self.assertGreater(timestamp.AsMicrosecondsSinceEpoch(), 0)
    self.assertCountEqual(list(blobs_iter), test_blobs)

  def testReadIndividualBlobsFromSignedBinary(self):
    test_urn = rdfvalue.RDFURN("aff4:/config/executables/foo")
    test_blobs = [
        rdf_crypto.SignedBlob().Sign(b"\x00\x11\x22", self._private_key),
        rdf_crypto.SignedBlob().Sign(b"\x33\x44\x55", self._private_key),
        rdf_crypto.SignedBlob().Sign(b"\x66\x77\x88", self._private_key),
        rdf_crypto.SignedBlob().Sign(b"\x99", self._private_key)
    ]
    signed_binary_utils.WriteSignedBinaryBlobs(test_urn, test_blobs)

    with self.assertRaises(ValueError):
      signed_binary_utils.FetchBlobForSignedBinaryByURN(test_urn, -1)

    for i, test_blob in enumerate(test_blobs):
      blob = signed_binary_utils.FetchBlobForSignedBinaryByURN(test_urn, i)
      self.assertEqual(blob.data, test_blob.data)

    with self.assertRaises(signed_binary_utils.BlobIndexOutOfBoundsError):
      signed_binary_utils.FetchBlobForSignedBinaryByURN(test_urn,
                                                        len(test_blobs))

  def testFetchSizeOfSignedBinary(self):
    binary1_urn = rdfvalue.RDFURN("aff4:/config/executables/foo1")
    binary2_urn = rdfvalue.RDFURN("aff4:/config/executables/foo2")
    binary1_data = b"\x00\x11\x22\x33\x44\x55\x66\x77\x88\x99"
    binary2_blobs = [
        rdf_crypto.SignedBlob().Sign(b"\x00\x11\x22", self._private_key),
        rdf_crypto.SignedBlob().Sign(b"\x33\x44", self._private_key)
    ]
    signed_binary_utils.WriteSignedBinary(
        binary1_urn,
        binary1_data,
        private_key=self._private_key,
        public_key=self._public_key,
        chunk_size=3)
    signed_binary_utils.WriteSignedBinaryBlobs(binary2_urn, binary2_blobs)
    binary1_size = signed_binary_utils.FetchSizeOfSignedBinary(binary1_urn)
    binary2_size = signed_binary_utils.FetchSizeOfSignedBinary(binary2_urn)
    self.assertEqual(binary1_size, 10)
    self.assertEqual(binary2_size, 5)

  def testDeleteSignedBinary(self):
    binary1_urn = rdfvalue.RDFURN("aff4:/config/executables/foo1")
    binary2_urn = rdfvalue.RDFURN("aff4:/config/executables/foo2")
    signed_binary_utils.WriteSignedBinaryBlobs(
        binary1_urn, [rdf_crypto.SignedBlob().Sign(b"\x00", self._private_key)])
    signed_binary_utils.WriteSignedBinaryBlobs(
        binary2_urn, [rdf_crypto.SignedBlob().Sign(b"\x11", self._private_key)])
    self.assertCountEqual(signed_binary_utils.FetchURNsForAllSignedBinaries(),
                          [binary1_urn, binary2_urn])
    signed_binary_utils.DeleteSignedBinary(binary1_urn)
    self.assertCountEqual(signed_binary_utils.FetchURNsForAllSignedBinaries(),
                          [binary2_urn])

  def testMissingSignedBinary(self):
    missing_urn = rdfvalue.RDFURN("aff4:/config/executables/not/exist")
    with self.assertRaises(signed_binary_utils.SignedBinaryNotFoundError):
      signed_binary_utils.DeleteSignedBinary(missing_urn)
    with self.assertRaises(signed_binary_utils.SignedBinaryNotFoundError):
      signed_binary_utils.FetchBlobsForSignedBinaryByURN(missing_urn)
    with self.assertRaises(signed_binary_utils.SignedBinaryNotFoundError):
      signed_binary_utils.FetchSizeOfSignedBinary(missing_urn)

  def _WriteTestBinaryAndGetBlobIterator(self, binary_data, chunk_size):
    binary_urn = rdfvalue.RDFURN("aff4:/config/executables/foo")
    signed_binary_utils.WriteSignedBinary(
        binary_urn,
        binary_data,
        private_key=self._private_key,
        public_key=self._public_key,
        chunk_size=chunk_size)
    blob_iterator, _ = signed_binary_utils.FetchBlobsForSignedBinaryByURN(
        binary_urn)
    return blob_iterator

  def testStreamSignedBinary_SmallBlobs(self):
    binary_data = b"\x00\x11\x22\x33\x44\x55\x66\x77\x88\x99\xaa\xbb\xcc\xdd"
    blob_iterator = self._WriteTestBinaryAndGetBlobIterator(binary_data, 3)
    # Stream binary content with a stream chunk size larger than the
    # size of individual blobs.
    chunk_generator = signed_binary_utils.StreamSignedBinaryContents(
        blob_iterator, chunk_size=4)
    expected_chunks = [
        b"\x00\x11\x22\x33",
        b"\x44\x55\x66\x77",
        b"\x88\x99\xaa\xbb",
        b"\xcc\xdd",
    ]
    self.assertCountEqual(list(chunk_generator), expected_chunks)

  def testStreamSignedBinary_LargeBlobs(self):
    binary_data = b"\x00\x11\x22\x33\x44\x55\x66\x77\x88\x99\xaa\xbb\xcc\xdd"
    blob_iterator = self._WriteTestBinaryAndGetBlobIterator(binary_data, 5)
    # Stream binary content with a stream chunk size smaller than the
    # size of individual blobs.
    chunk_generator = signed_binary_utils.StreamSignedBinaryContents(
        blob_iterator, chunk_size=4)
    expected_chunks = [
        b"\x00\x11\x22\x33",
        b"\x44\x55\x66\x77",
        b"\x88\x99\xaa\xbb",
        b"\xcc\xdd",
    ]
    self.assertCountEqual(list(chunk_generator), expected_chunks)

  def testStreamSignedBinary_SingleChunk(self):
    binary_data = b"\x00\x11\x22\x33\x44\x55\x66\x77\x88\x99\xaa\xbb\xcc\xdd"
    blob_iterator = self._WriteTestBinaryAndGetBlobIterator(binary_data, 5)
    # Stream binary content with a chunk size larger than the size of the
    # binary.
    chunk_generator = signed_binary_utils.StreamSignedBinaryContents(
        blob_iterator, chunk_size=15)
    self.assertCountEqual(list(chunk_generator), [binary_data])

  def testUpdateSignedBinary(self):
    binary1_data = b"\x00\x11\x22\x33"
    binary2_data = b"\x44\x55\x66\x77"
    self._WriteTestBinaryAndGetBlobIterator(binary1_data, 10)
    blob_iterator = self._WriteTestBinaryAndGetBlobIterator(binary2_data, 10)
    chunk_generator = signed_binary_utils.StreamSignedBinaryContents(
        blob_iterator, chunk_size=10)
    self.assertCountEqual(list(chunk_generator), [binary2_data])


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
