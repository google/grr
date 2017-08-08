#!/usr/bin/env python
"""Test the Upload functionality."""
import gzip
import StringIO

from grr.lib import flags
from grr.lib import uploads
from grr.lib.rdfvalues import crypto
from grr.test_lib import test_lib


class UploadTests(test_lib.GRRBaseTest):
  """Test the upload stream wrapper."""

  def setUp(self):
    super(UploadTests, self).setUp()
    self.readers_private_key = crypto.RSAPrivateKey().GenerateKey()
    self.writers_private_key = crypto.RSAPrivateKey().GenerateKey()

    self.test_string = "Hello world" * 500

    self.infd = StringIO.StringIO(self.test_string)
    self.outfd = StringIO.StringIO()

    self.encrypt_wrapper = uploads.EncryptStream(
        readers_public_key=self.readers_private_key.GetPublicKey(),
        writers_private_key=self.writers_private_key,
        fd=self.infd,
        chunk_size=1024)

    self.decrypt_wrapper = uploads.DecryptStream(
        readers_private_key=self.readers_private_key,
        writers_public_key=self.writers_private_key.GetPublicKey(),
        outfd=self.outfd)

  def testKeyMismatch(self):
    """Checks the performance impact of reusing stolen upload tokens.

    Upload policies are HMAC'd by the server only so they can be
    grabbed from the wire and reused to perform a DOS attack. To limit
    the impact of this attack, we need to bail out as soon as possible
    once we realize we are handed a stream that was not encrypted with
    the client key that is indicated in the policy.
    """
    encrypted_data = self.encrypt_wrapper.read(1024 * 1024 * 100)

    wrong_key = crypto.RSAPrivateKey().GenerateKey()
    decrypt_wrapper = uploads.DecryptStream(
        readers_private_key=self.readers_private_key,
        writers_public_key=wrong_key.GetPublicKey(),
        outfd=self.outfd)

    # We should know after very few bytes that the key is wrong. The
    # first encrypted chunk is the serialized signature which is 518
    # bytes in the test. Adding crypto headers gives a chunk size of
    # 570. After 600 bytes we should definitely bail out.
    with self.assertRaises(crypto.VerificationError):
      decrypt_wrapper.write(encrypted_data[:600])

  def testUploadWrapper(self):
    """Check that encryption/decryption of the streams works."""
    # Check that small reads still work.
    encrypted_data = ""
    while 1:
      small_read = self.encrypt_wrapper.read(2)
      if not small_read:
        break

      # Make sure that the reads are not larger than requested.
      self.assertTrue(len(small_read) <= 2)

      encrypted_data += small_read

      self.decrypt_wrapper.write(small_read)

    self.assertEqual(self.test_string, self.outfd.getvalue())

  def testUploadWrapperWithLargeWrites(self):
    """Make sure large reads and writes works."""
    # Read all the data at once.
    encrypted_data = self.encrypt_wrapper.read(1024 * 1024 * 100)

    # Write all the data at once.
    self.decrypt_wrapper.write(encrypted_data)

    self.assertEqual(self.test_string, self.outfd.getvalue())

  def testUploadWrapperCorruption(self):
    """Check that corruption of encrypted stream is detected."""
    # Check that small reads still work.
    encrypted_data = ""
    count = 0
    with self.assertRaisesRegexp(IOError, "HMAC not verified"):
      while 1:
        small_read = self.encrypt_wrapper.read(2)
        if not small_read:
          break
        encrypted_data += small_read
        count += len(small_read)

        # Corrupt the data a little bit.
        if count == 3000:
          small_read = "XX"

        self.decrypt_wrapper.write(small_read)

  def testUploadWrapperPartialTransfer(self):
    """Check that partial transfer is detected."""
    # Check that small reads still work.
    encrypted_data = ""
    count = 0
    while 1:
      small_read = self.encrypt_wrapper.read(2)
      if not small_read:
        break
      encrypted_data += small_read
      count += len(small_read)

      # Exit this loop sooner than it needs to.
      if count == 6000:
        break

      self.decrypt_wrapper.write(small_read)

    # This should raise a HMAC error because the tranfer is too short.
    with self.assertRaisesRegexp(IOError, "Partial Message Received"):
      self.decrypt_wrapper.close()

    # But the data sent up until the corruption is still saved. At least 4
    # chunks.
    self.assertTrue(len(self.outfd.getvalue()) >= 4096)

  def testGzipWrapper(self):
    gzip_data = uploads.GzipWrapper(self.infd).read(10000)
    fd = gzip.GzipFile(mode="r", fileobj=StringIO.StringIO(gzip_data))
    self.assertEqual(fd.read(), self.test_string)

  def testGzipWrapperSmallReads(self):
    gzip_fd = uploads.GzipWrapper(self.infd)
    gzip_data = ""
    while True:
      chunk = gzip_fd.read(5)
      if not chunk:
        break
      gzip_data += chunk

    fd = gzip.GzipFile(mode="r", fileobj=StringIO.StringIO(gzip_data))
    self.assertEqual(fd.read(), self.test_string)

  def testGzipWrapperLimit(self):
    gzip_data = uploads.GzipWrapper(self.infd, byte_limit=100).read(10000)
    fd = gzip.GzipFile(mode="r", fileobj=StringIO.StringIO(gzip_data))
    self.assertEqual(fd.read(), self.test_string[:100])

  def testGUnzipWrapper(self):
    gzip_data = uploads.GzipWrapper(self.infd).read(10000)
    outfd = StringIO.StringIO()
    uploads.GunzipWrapper(outfd).write(gzip_data)
    self.assertEqual(outfd.getvalue(), self.test_string)

    outfd = StringIO.StringIO()
    wrapped = uploads.GunzipWrapper(outfd)
    for c in gzip_data:
      wrapped.write(c)
    self.assertEqual(outfd.getvalue(), self.test_string)


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
