#!/usr/bin/env python
import binascii
import os

from absl.testing import absltest

from grr_response_server.models import blobs as models_blobs


class BlobIDTest(absltest.TestCase):

  def testEqualTrue(self):
    blob_id = models_blobs.BlobID(os.urandom(32))
    self.assertEqual(blob_id, blob_id)

  def testEqualFalse(self):
    blob_id_1 = models_blobs.BlobID(b"0123456789ABCDEF0123456789ABCDEF")
    blob_id_2 = models_blobs.BlobID(b"9876543210FEDCBA9876543210FEDCBA")
    self.assertNotEqual(blob_id_1, blob_id_2)

  def testBytes(self):
    sha256 = os.urandom(32)
    self.assertEqual(bytes(models_blobs.BlobID(sha256)), sha256)

  def testStr(self):
    blob_id = models_blobs.BlobID(b"\xfa\x07" * 16)
    self.assertEqual(
        str(blob_id),
        "BlobID(fa07fa07fa07fa07fa07fa07fa07fa07fa07fa07fa07fa07fa07fa07fa07fa07)",
    )

  def testRepr(self):
    blob_id = models_blobs.BlobID(b"012345678901234567890123456789\xff\x00")
    self.assertEqual(
        repr(blob_id),
        r"BlobID(b'012345678901234567890123456789\xff\x00')",
    )

  def testReprEval(self):
    blob_id = models_blobs.BlobID(os.urandom(32))
    self.assertEqual(
        eval(repr(blob_id), {}, {"BlobID": models_blobs.BlobID}),  # pylint: disable=eval-used
        blob_id,
    )

  def testHashEqual(self):
    blob_id_1 = models_blobs.BlobID(b"0123456789ABCDEF0123456789ABCDEF")
    blob_id_2 = models_blobs.BlobID(b"0123456789ABCDEF0123456789ABCDEF")
    self.assertEqual(blob_id_1, blob_id_2)

  def testHashNotEqual(self):
    blob_id_1 = models_blobs.BlobID(b"0123456789ABCDEF0123456789ABCDEF")
    blob_id_2 = models_blobs.BlobID(b"9876543210FEDCBA9876543210FEDCBA")
    self.assertNotEqual(hash(blob_id_1), hash(blob_id_2))

  def testOf(self):
    text = "Lorem ipsum dolor sit amet."
    sha256 = "dd14cbbf0e74909aac7f248a85d190afd8da98265cef95fc90dfddabea7c2e66"

    self.assertEqual(
        models_blobs.BlobID.Of(text.encode("utf-8")),
        models_blobs.BlobID(binascii.unhexlify(sha256)),
    )


if __name__ == "__main__":
  absltest.main()
