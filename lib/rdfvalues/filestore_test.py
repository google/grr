#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

"""These are tests for the file store-related RDFValues implementations."""



from grr.lib.aff4_objects import filestore
from grr.lib.rdfvalues import test_base


class FileStoreHashTest(test_base.RDFValueTestCase):
  """Test the FileStoreHash implementation."""

  rdfvalue_class = filestore.FileStoreHash

  def CheckRDFValue(self, value, sample):
    """Check that the rdfproto is the same as the sample."""
    super(FileStoreHashTest, self).CheckRDFValue(value, sample)

    self.assertEqual(value.fingerprint_type, sample.fingerprint_type)
    self.assertEqual(value.hash_type, sample.hash_type)
    self.assertEqual(value.hash_value, sample.hash_value)

  def GenerateSample(self, number=0):
    """Make a sample FileStoreHash instance."""
    return filestore.FileStoreHash(
        "aff4:/files/hash/pecoff/sha1/"
        "eb875812858d27b22cb2b75f992dffadc1b05c6%d" % number)

  def testHashIsInferredCorrectlyFromTheURN(self):
    """Test we can initialized a hash from the HashFileStore urn."""
    sample = self.GenerateSample()
    self.assertEqual(sample.fingerprint_type, "pecoff")
    self.assertEqual(sample.hash_type, "sha1")
    self.assertEqual(sample.hash_value,
                     "eb875812858d27b22cb2b75f992dffadc1b05c60")

  def testHashIsInitializedFromConstructorArguments(self):
    """Test that we can construct FileStoreHash from keyword arguments."""
    sample = filestore.FileStoreHash(
        fingerprint_type="pecoff", hash_type="sha1",
        hash_value="eb875812858d27b22cb2b75f992dffadc1b05c60")
    self.assertEqual(sample, self.GenerateSample())

  def testInitialization(self):
    # Invalid URN prefix
    self.assertRaises(
        ValueError, filestore.FileStoreHash,
        "aff4:/sha1/eb875812858d27b22cb2b75f992dffadc1b05c66")

    # Invalid fingerprint type
    self.assertRaises(
        ValueError, filestore.FileStoreHash,
        "aff4:/files/hash/_/sha1/eb875812858d27b22cb2b75f992dffadc1b05c66")

    # Invalid hash type
    self.assertRaises(
        ValueError, filestore.FileStoreHash,
        "aff4:/files/hash/pecoff/_/eb875812858d27b22cb2b75f992dffadc1b05c66")

    # Additional path components
    self.assertRaises(
        ValueError, filestore.FileStoreHash,
        "aff4:/files/hash/pecoff/sha1/eb875812858d27b22cb2b75f992dffadc1b05c66/"
        "_")
