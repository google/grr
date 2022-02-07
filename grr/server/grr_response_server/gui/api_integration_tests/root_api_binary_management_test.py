#!/usr/bin/env python
"""Tests for root API user management calls."""

import io

from absl import app

from grr_api_client import errors as grr_api_errors
from grr_response_core import config as config
from grr_response_core.lib.rdfvalues import crypto as rdf_crypto
from grr_response_proto.api import config_pb2
from grr_response_server.gui import api_integration_test_lib
from grr.test_lib import test_lib


class RootApiBinaryManagementTest(
    api_integration_test_lib.RootApiIntegrationTest):
  """E2E test for root API user management calls."""

  def _Upload(self, binary_type, path, data, private_key=None):
    if not private_key:
      private_key = config.CONFIG["PrivateKeys.executable_signing_private_key"]

    sio = io.BytesIO()
    sio.write(data)
    sio.seek(0)

    binary = self.api.root.GrrBinary(binary_type, path)
    binary.Upload(
        sio,
        sign_fn=binary.DefaultUploadSigner(
            private_key=private_key.GetRawPrivateKey()))

  def _testBinaryUpload(self, binary_type, path, data, private_key=None):
    self._Upload(binary_type, path, data, private_key=private_key)

    read_binary = self.api.GrrBinary(binary_type, path).Get()
    self.assertTrue(read_binary.data.has_valid_signature)

    result_sio = io.BytesIO()
    read_binary.GetBlob().WriteToStream(result_sio)

    self.assertEqual(result_sio.getvalue(), data)

  def testUploadedPythonHackCanBeReadBack(self):
    self._testBinaryUpload(config_pb2.ApiGrrBinary.PYTHON_HACK,
                           "windows/clean.py", b"print 'blah'")

  def testUploadedExecutableCanBeReadBack(self):
    self._testBinaryUpload(config_pb2.ApiGrrBinary.EXECUTABLE, "windows/a.ps1",
                           b"# some")

  def testUploadedBinaryWithIncorrectSignatureIsCorrectlyReported(self):
    private_key = rdf_crypto.RSAPrivateKey.GenerateKey()
    self._Upload(
        config_pb2.ApiGrrBinary.EXECUTABLE,
        "windows/a.ps1",
        b"# some",
        private_key=private_key)

    read_binary = self.api.GrrBinary(config_pb2.ApiGrrBinary.EXECUTABLE,
                                     "windows/a.ps1").Get()
    self.assertFalse(read_binary.data.has_valid_signature)

  def testLargeUploadedExecutableCanBeReadBack(self):
    # 5Mb of data
    data = b"#" * 1024 * 1024 * 5
    self._testBinaryUpload(config_pb2.ApiGrrBinary.EXECUTABLE, "windows/a.ps1",
                           data)

  def testBinariesCanBeOverwritten(self):
    self._testBinaryUpload(config_pb2.ApiGrrBinary.PYTHON_HACK,
                           "windows/clean.py", b"print 'foo'")
    self._testBinaryUpload(config_pb2.ApiGrrBinary.PYTHON_HACK,
                           "windows/clean.py", b"print 'bar'")

  def testBinariesCanNotBeOverwrittenIfReadOnlyConfigOptionIsSet(self):
    with test_lib.ConfigOverrider({"Server.grr_binaries_readonly": True}):
      self._testBinaryUpload(config_pb2.ApiGrrBinary.PYTHON_HACK,
                             "windows/clean.py", b"print 'foo'")

      with self.assertRaises(grr_api_errors.AccessForbiddenError):
        self._Upload(config_pb2.ApiGrrBinary.PYTHON_HACK, "windows/clean.py",
                     b"print 'bar'")

  def testDeletionFailsWhenBinaryNotFound(self):
    with self.assertRaises(grr_api_errors.ResourceNotFoundError):
      self.api.root.GrrBinary(config_pb2.ApiGrrBinary.EXECUTABLE,
                              "windows/a.ps1").Delete()

  def testDeletionFailsIfReadOnlyConfigOptionIsSet(self):
    with test_lib.ConfigOverrider({"Server.grr_binaries_readonly": True}):
      self._testBinaryUpload(config_pb2.ApiGrrBinary.EXECUTABLE,
                             "windows/a.ps1", b"blah")

      with self.assertRaises(grr_api_errors.AccessForbiddenError):
        self.api.root.GrrBinary(config_pb2.ApiGrrBinary.EXECUTABLE,
                                "windows/a.ps1").Delete()

  def testUploadedBinaryIsCorrectlyDeleted(self):
    self._testBinaryUpload(config_pb2.ApiGrrBinary.EXECUTABLE, "windows/a.ps1",
                           b"blah")
    self.api.root.GrrBinary(config_pb2.ApiGrrBinary.EXECUTABLE,
                            "windows/a.ps1").Delete()


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
