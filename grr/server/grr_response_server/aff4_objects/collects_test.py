#!/usr/bin/env python
"""Test the various collection objects."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core import config
from grr_response_core.lib import flags
from grr_response_server import aff4
from grr_response_server.aff4_objects import collects
from grr.test_lib import aff4_test_lib
from grr.test_lib import test_lib


class TestCollections(aff4_test_lib.AFF4ObjectTest):

  def testGRRSignedBlob(self):
    urn = "aff4:/test/collection"

    # The only way to create a GRRSignedBlob is via this constructor.
    fd = collects.GRRSignedBlob.NewFromContent(
        b"hello world",
        urn,
        chunk_size=2,
        token=self.token,
        private_key=config.CONFIG["PrivateKeys.executable_signing_private_key"],
        public_key=config.CONFIG["Client.executable_signing_public_key"])

    fd = aff4.FACTORY.Open(urn, token=self.token)

    # Reading works as expected.
    self.assertEqual(fd.read(10000), "hello world")
    self.assertEqual(fd.size, 11)

    # We have 6 collections.
    self.assertLen(fd.collection, 6)

    # Chunking works ok.
    self.assertEqual(fd.collection[0].data, "he")
    self.assertEqual(fd.collection[1].data, "ll")

    # GRRSignedBlob does not support writing.
    self.assertRaises(IOError, fd.write, "foo")

  def _NewFromString(self, urn, string):
    collects.GRRSignedBlob.NewFromContent(
        string,
        urn,
        private_key=config.CONFIG["PrivateKeys.executable_signing_private_key"],
        public_key=config.CONFIG["Client.executable_signing_public_key"],
        token=self.token)

  def testSignedBlob(self):
    test_string = b"Sample 5"

    urn = "aff4:/test/signedblob"
    self._NewFromString(urn, test_string)

    sample = aff4.FACTORY.Open(urn, token=self.token)
    self.assertEqual(sample.size, len(test_string))
    self.assertEqual(sample.Tell(), 0)
    self.assertEqual(sample.Read(3), test_string[:3])
    self.assertEqual(sample.Tell(), 3)
    self.assertEqual(sample.Read(30), test_string[3:])
    self.assertEqual(sample.Tell(), len(test_string))
    self.assertEqual(sample.Read(30), "")
    sample.Seek(3)
    self.assertEqual(sample.Tell(), 3)
    self.assertEqual(sample.Read(3), test_string[3:6])

  def testSignedBlobDeletion(self):
    test_string = b"Sample 5"

    urn = "aff4:/test/signedblobdel"
    self._NewFromString(urn, test_string)

    sample = aff4.FACTORY.Open(urn, token=self.token)

    aff4.FACTORY.Delete(urn, token=self.token)

    # Recreate in the same place.
    test_string = b"Sample 4"
    self._NewFromString(urn, test_string)

    sample = aff4.FACTORY.Open(urn, token=self.token)

    self.assertEqual(sample.size, len(test_string))
    self.assertEqual(sample.Tell(), 0)
    self.assertEqual(sample.Read(len(test_string)), test_string)


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
