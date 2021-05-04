#!/usr/bin/env python
import io
import os
from unittest import mock

from absl.testing import absltest
import responses

from grr_response_client import vfs
from grr_response_client.client_actions import large_file
from grr_response_client.vfs_handlers import files
from grr_response_core.lib.rdfvalues import large_file as rdf_large_file
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.util import aead
from grr_response_core.lib.util import temp
from grr.test_lib import gcs_test_lib


class CollectLargeFileTest(absltest.TestCase):

  # TODO(hanuszczak): Migrate to `setUpClass` once we are on Python 3.8 (because
  # of `addCleanupClass`).
  def setUp(self):
    super().setUp()

    vfs_patcher = mock.patch.object(vfs, "VFS_HANDLERS", {
        rdf_paths.PathSpec.PathType.OS: files.File,
    })
    vfs_patcher.start()
    self.addCleanup(vfs_patcher.stop)

  def testNoEncryptionKey(self):
    with temp.AutoTempFilePath() as temppath:
      args = rdf_large_file.CollectLargeFileArgs()
      args.path_spec.path = temppath
      args.path_spec.pathtype = rdf_paths.PathSpec.PathType.OS

      with self.assertRaisesRegex(ValueError, "key"):
        list(large_file.CollectLargeFile(args))

  def testIncorrectEncryptionKey(self):
    with temp.AutoTempFilePath() as temppath:
      args = rdf_large_file.CollectLargeFileArgs()
      args.path_spec.path = temppath
      args.path_spec.pathtype = rdf_paths.PathSpec.PathType.OS
      args.encryption_key = b"123456"

      with self.assertRaisesRegex(ValueError, "key"):
        list(large_file.CollectLargeFile(args))

  def testRandomPaddedFile(self):
    self._testFile(os.urandom(16 * 1024 * 1024))

  def testRandomUnpaddedFile(self):
    self._testFile(os.urandom(16_379_119))

  @responses.activate
  def _testFile(self, content: bytes):  # pylint: disable=invalid-name
    key = os.urandom(32)

    response = responses.Response(responses.POST, "https://foo.bar/quux")
    response.status = 201
    response.headers = {
        "Location": "https://foo.bar/norf",
    }
    responses.add(response)

    handler = gcs_test_lib.FakeUploadHandler()
    responses.add_callback(responses.PUT, "https://foo.bar/norf", handler)

    with temp.AutoTempDirPath(remove_non_empty=True) as tempdir:
      with open(os.path.join(tempdir, "file"), mode="wb") as file:
        file.write(content)

      args = rdf_large_file.CollectLargeFileArgs()
      args.signed_url = "https://foo.bar/quux"
      args.encryption_key = key
      args.path_spec.pathtype = rdf_paths.PathSpec.PathType.OS
      args.path_spec.path = os.path.join(tempdir, "file")

      results = list(large_file.CollectLargeFile(args))

    self.assertLen(results, 1)
    self.assertEqual(results[0].session_uri, "https://foo.bar/norf")

    encrypted_buf = io.BytesIO(handler.content)
    decrypted_buf = aead.Decrypt(encrypted_buf, key)
    self.assertEqual(decrypted_buf.read(), content)


if __name__ == "__main__":
  absltest.main()
