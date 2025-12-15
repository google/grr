#!/usr/bin/env python
"""Test client standard actions."""

import hashlib
import io
import os
import platform
import stat
import sys
import unittest
from unittest import mock

from absl import app

from grr_response_client.client_actions import standard
from grr_response_client.vfs_handlers import files
from grr_response_core import config
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_action as rdf_client_action
from grr_response_core.lib.rdfvalues import crypto as rdf_crypto
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_core.lib.util import temp
from grr.test_lib import action_mocks
from grr.test_lib import client_test_lib
from grr.test_lib import filesystem_test_lib
from grr.test_lib import test_lib


class TestExecutePython(client_test_lib.EmptyActionTest):
  """Test the client execute actions."""

  def setUp(self):
    super().setUp()
    self.signing_key = config.CONFIG[
        "PrivateKeys.executable_signing_private_key"
    ]

  def testExecutePython(self):
    """Test the basic ExecutePython action."""
    sys.TEST_VAL = "original"
    python_code = "import sys; sys.TEST_VAL = 'modified'"
    signed_blob = rdf_crypto.SignedBlob()
    signed_blob.Sign(python_code.encode("utf-8"), self.signing_key)
    request = rdf_client_action.ExecutePythonRequest(python_code=signed_blob)
    result = self.RunAction(standard.ExecutePython, request)[0]

    if platform.system() != "Windows":  # Windows time resolution is too coarse.
      self.assertGreater(result.time_used, 0)
    self.assertEqual(result.return_val, "")
    self.assertEqual(sys.TEST_VAL, "modified")

  def testExecutePythonEnvironment(self):
    """Test the basic ExecutePython action."""

    python_code = """
import io
import base64
import binascii

def decode(encoded):
  # Use the import (base64) inside a function. This will fail if the environment
  # for exec is not set up properly.
  return base64.b64decode(encoded)

s = "53475673624738675632397962475168"
s = binascii.unhexlify(s.encode("ascii"))

magic_return_str = decode(s)
"""
    signed_blob = rdf_crypto.SignedBlob()
    signed_blob.Sign(python_code.encode("utf-8"), self.signing_key)
    request = rdf_client_action.ExecutePythonRequest(python_code=signed_blob)
    result = self.RunAction(standard.ExecutePython, request)[0]

    if platform.system() != "Windows":  # Windows time resolution is too coarse.
      self.assertGreater(result.time_used, 0)
    self.assertEqual(result.return_val, "Hello World!")

  def testStdoutHooking(self):
    python_code = """

def f(n):
    print("F called: %s" % n)

print("Calling f.")
f(1)
print("Done.")
"""
    signed_blob = rdf_crypto.SignedBlob()
    signed_blob.Sign(python_code.encode("utf-8"), self.signing_key)
    request = rdf_client_action.ExecutePythonRequest(python_code=signed_blob)
    result = self.RunAction(standard.ExecutePython, request)[0]

    if platform.system() != "Windows":  # Windows time resolution is too coarse.
      self.assertGreater(result.time_used, 0)
    self.assertEqual(result.return_val, "Calling f.\nF called: 1\nDone.\n")

  def testProgress(self):
    python_code = """

def f():
    # This should also work inside a function.
    Progress()

f()
Progress()
print("Done.")
"""
    signed_blob = rdf_crypto.SignedBlob()
    signed_blob.Sign(python_code.encode("utf-8"), self.signing_key)
    request = rdf_client_action.ExecutePythonRequest(python_code=signed_blob)
    result = self.RunAction(standard.ExecutePython, request)[0]

    if platform.system() != "Windows":  # Windows time resolution is too coarse.
      self.assertGreater(result.time_used, 0)
    self.assertEqual(result.return_val, "Done.\n")

  def testExecuteModifiedPython(self):
    """Test that rejects invalid ExecutePython action."""
    sys.TEST_VAL = "original"
    python_code = "import sys; sys.TEST_VAL = 'modified'"
    signed_blob = rdf_crypto.SignedBlob()
    signed_blob.Sign(python_code.encode("utf-8"), self.signing_key)

    # Modify the data so the signature does not match.
    signed_blob.data = b"sys.TEST_VAL = 'notmodified'"

    request = rdf_client_action.ExecutePythonRequest(python_code=signed_blob)

    # Should raise since the code has been modified.
    self.assertRaises(
        rdf_crypto.VerificationError,
        self.RunAction,
        standard.ExecutePython,
        request,
    )

    # Lets also adjust the hash.
    signed_blob.digest = hashlib.sha256(signed_blob.data).digest()
    request = rdf_client_action.ExecutePythonRequest(python_code=signed_blob)

    self.assertRaises(
        rdf_crypto.VerificationError,
        self.RunAction,
        standard.ExecutePython,
        request,
    )

    # Make sure the code never ran.
    self.assertEqual(sys.TEST_VAL, "original")

  def testExecuteBrokenPython(self):
    """Test broken code raises back to the original flow."""
    python_code = "raise ValueError"
    signed_blob = rdf_crypto.SignedBlob()
    signed_blob.Sign(python_code.encode("utf-8"), self.signing_key)
    request = rdf_client_action.ExecutePythonRequest(python_code=signed_blob)

    self.assertRaises(
        ValueError, self.RunAction, standard.ExecutePython, request
    )

  def testExecuteBinary(self):
    """Test the basic ExecuteBinaryCommand action."""
    if platform.system() == "Windows":
      cmd, args = r"C:\Windows\System32\cmd.exe", ["/C", "echo", "foobar"]
    else:
      cmd, args = "/bin/echo", ["foobar"]

    signed_blob = rdf_crypto.SignedBlob()
    signed_blob.Sign(open(cmd, "rb").read(), self.signing_key)

    request = rdf_client_action.ExecuteBinaryRequest(
        executable=signed_blob, args=args, write_path="ablob"
    )

    result = self.RunAction(standard.ExecuteBinaryCommand, request)[0]

    if platform.system() != "Windows":  # Windows time resolution is too coarse.
      self.assertGreater(result.time_used, 0)
    self.assertEqual(
        "foobar{}".format(os.linesep).encode("utf-8"), result.stdout
    )

  def testReturnVals(self):
    """Test return values."""
    python_code = "magic_return_str = 'return string'"
    signed_blob = rdf_crypto.SignedBlob()
    signed_blob.Sign(python_code.encode("utf-8"), self.signing_key)
    request = rdf_client_action.ExecutePythonRequest(python_code=signed_blob)
    result = self.RunAction(standard.ExecutePython, request)[0]

    self.assertEqual(result.return_val, "return string")

  def testWrongKey(self):
    """Test return values."""
    python_code = "print 'test'"

    # Generate a test valid RSA key that isn't the real one.
    signing_key = rdf_crypto.RSAPrivateKey.GenerateKey(2048, 65537)
    signed_blob = rdf_crypto.SignedBlob()
    signed_blob.Sign(python_code.encode("utf-8"), signing_key)
    request = rdf_client_action.ExecutePythonRequest(python_code=signed_blob)
    self.assertRaises(
        rdf_crypto.VerificationError,
        self.RunAction,
        standard.ExecutePython,
        request,
    )

  def testArgs(self):
    """Test passing arguments."""
    sys.TEST_VAL = "original"
    python_code = """
import sys

magic_return_str = py_args['test']
sys.TEST_VAL = py_args[43]
"""
    signed_blob = rdf_crypto.SignedBlob()
    signed_blob.Sign(python_code.encode("utf-8"), self.signing_key)
    pdict = rdf_protodict.Dict({"test": "dict_arg", 43: "dict_arg2"})
    request = rdf_client_action.ExecutePythonRequest(
        python_code=signed_blob, py_args=pdict
    )
    result = self.RunAction(standard.ExecutePython, request)[0]
    self.assertEqual(result.return_val, "dict_arg")
    self.assertEqual(sys.TEST_VAL, "dict_arg2")


class GetFileStatTest(client_test_lib.EmptyActionTest):

  # TODO:
  @unittest.skipIf(
      platform.system() == "Windows",
      "Skipping due to temp file locking issues.",
  )
  def testStatSize(self):
    with temp.AutoTempFilePath() as temp_filepath:
      with io.open(temp_filepath, "wb") as temp_file:
        temp_file.write(b"123456")

      pathspec = rdf_paths.PathSpec(
          path=temp_filepath, pathtype=rdf_paths.PathSpec.PathType.OS
      )

      request = rdf_client_action.GetFileStatRequest(pathspec=pathspec)
      results = self.RunAction(standard.GetFileStat, request)

      self.assertLen(results, 1)
      self.assertEqual(results[0].st_size, 6)

  def testStatExtAttrsEnabled(self):
    with temp.AutoTempFilePath() as temp_filepath:
      filesystem_test_lib.SetExtAttr(
          temp_filepath, name="user.foo", value="bar"
      )

      pathspec = rdf_paths.PathSpec(
          path=temp_filepath, pathtype=rdf_paths.PathSpec.PathType.OS
      )

      request = rdf_client_action.GetFileStatRequest(
          pathspec=pathspec, collect_ext_attrs=True
      )
      results = self.RunAction(standard.GetFileStat, request)

      self.assertLen(results, 1)
      self.assertLen(results[0].ext_attrs, 1)
      self.assertEqual(results[0].ext_attrs[0].name, b"user.foo")
      self.assertEqual(results[0].ext_attrs[0].value, b"bar")

  def testStatExtAttrsDisabled(self):
    with temp.AutoTempFilePath() as temp_filepath:
      filesystem_test_lib.SetExtAttr(
          temp_filepath, name="user.foo", value="bar"
      )

      pathspec = rdf_paths.PathSpec(
          path=temp_filepath, pathtype=rdf_paths.PathSpec.PathType.OS
      )

      request = rdf_client_action.GetFileStatRequest(
          pathspec=pathspec, collect_ext_attrs=False
      )
      results = self.RunAction(standard.GetFileStat, request)

      self.assertLen(results, 1)
      self.assertEmpty(results[0].ext_attrs)

  def testFollowSymlinkEnabled(self):
    data = b"quux" * 1024

    with temp.AutoTempDirPath(remove_non_empty=True) as temp_dirpath:
      target_filepath = os.path.join(temp_dirpath, "target")
      symlink_filepath = os.path.join(temp_dirpath, "symlink")

      filesystem_test_lib.CreateFile(target_filepath, data)
      os.symlink(target_filepath, symlink_filepath)

      request = rdf_client_action.GetFileStatRequest()
      request.pathspec = rdf_paths.PathSpec.OS(path=symlink_filepath)
      request.follow_symlink = True

      results = self.RunAction(standard.GetFileStat, request)

      self.assertLen(results, 1)
      self.assertFalse(stat.S_ISLNK(int(results[0].st_mode)))
      self.assertEqual(results[0].st_size, len(data))

      # TODO: Required to clean-up the temp directory.
      files.FlushHandleCache()

  def testFollowSymlinkDisable(self):
    data = b"thud" * 1024

    with temp.AutoTempDirPath(remove_non_empty=True) as temp_dirpath:
      target_filepath = os.path.join(temp_dirpath, "target")
      symlink_filepath = os.path.join(temp_dirpath, "symlink")

      filesystem_test_lib.CreateFile(target_filepath, data)
      os.symlink(target_filepath, symlink_filepath)

      request = rdf_client_action.GetFileStatRequest()
      request.pathspec = rdf_paths.PathSpec.OS(path=symlink_filepath)
      request.follow_symlink = False

      results = self.RunAction(standard.GetFileStat, request)

      self.assertLen(results, 1)
      self.assertTrue(stat.S_ISLNK(int(results[0].st_mode)))
      self.assertLess(results[0].st_size, len(data))
      self.assertEqual(results[0].symlink, target_filepath)

      # TODO: Required to clean-up the temp directory.
      files.FlushHandleCache()


class TestNetworkByteLimits(client_test_lib.EmptyActionTest):
  """Test TransferBuffer network byte limits."""

  def setUp(self):
    super().setUp()
    pathspec = rdf_paths.PathSpec(
        path="/nothing", pathtype=rdf_paths.PathSpec.PathType.OS
    )
    self.buffer_ref = rdf_client.BufferReference(pathspec=pathspec, length=5000)
    self.data = b"X" * 500

    stubber = mock.patch.object(standard.vfs, "ReadVFS", return_value=self.data)
    stubber.start()
    self.addCleanup(stubber.stop)

    self.transfer_buf = action_mocks.ActionMock(standard.TransferBuffer)

  def testTransferNetworkByteLimitError(self):
    message = rdf_flows.GrrMessage(
        name="TransferBuffer",
        payload=self.buffer_ref,
        network_bytes_limit=300,
    )

    # We just get a client alert and a status message back.
    responses = self.transfer_buf.HandleMessage(message)

    client_alert = responses[0].payload
    self.assertIn("Network limit exceeded", str(client_alert))

    status = responses[1].payload
    self.assertIn("Action exceeded network send limit", str(status.backtrace))
    self.assertEqual(
        status.status, rdf_flows.GrrStatus.ReturnedStatus.NETWORK_LIMIT_EXCEEDED
    )

  def testTransferNetworkByteLimit(self):
    message = rdf_flows.GrrMessage(
        name="TransferBuffer",
        payload=self.buffer_ref,
        network_bytes_limit=900,
    )

    responses = self.transfer_buf.HandleMessage(message)

    for response in responses:
      if isinstance(response, rdf_flows.GrrStatus):
        self.assertEqual(
            response.payload.status, rdf_flows.GrrStatus.ReturnedStatus.OK
        )


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
