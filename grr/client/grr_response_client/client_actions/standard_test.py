#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Test client standard actions."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import gzip
import hashlib
import os
import time


from grr_response_client.client_actions import standard
from grr_response_core import config
from grr_response_core.lib import flags
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_action as rdf_client_action
from grr_response_core.lib.rdfvalues import crypto as rdf_crypto
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr.test_lib import action_mocks
from grr.test_lib import client_test_lib
from grr.test_lib import temp
from grr.test_lib import test_lib


class TestExecutePython(client_test_lib.EmptyActionTest):
  """Test the client execute actions."""

  def setUp(self):
    super(TestExecutePython, self).setUp()
    self.signing_key = config.CONFIG[
        "PrivateKeys.executable_signing_private_key"]

  def testExecutePython(self):
    """Test the basic ExecutePython action."""
    utils.TEST_VAL = "original"
    python_code = "utils.TEST_VAL = 'modified'"
    signed_blob = rdf_crypto.SignedBlob()
    signed_blob.Sign(python_code.encode("utf-8"), self.signing_key)
    request = rdf_client_action.ExecutePythonRequest(python_code=signed_blob)
    result = self.RunAction(standard.ExecutePython, request)[0]

    self.assertGreater(result.time_used, 0)
    self.assertEqual(result.return_val, "")
    self.assertEqual(utils.TEST_VAL, "modified")

  def testExecutePythonEnvironment(self):
    """Test the basic ExecutePython action."""

    python_code = """
import io
import uu

def decode(encoded):
  # Use the import (uu) inside a function. This will fail if the environment
  # for exec is not set up properly.
  i = io.BytesIO(s)
  o = io.BytesIO()
  uu.decode(i, o)
  return o.getvalue()

s = "626567696e20363636202d0a2c3226354c3b265c4035565d523b2630410a200a656e640a"
s = s.decode("hex")

magic_return_str = decode(s)
"""
    signed_blob = rdf_crypto.SignedBlob()
    signed_blob.Sign(python_code.encode("utf-8"), self.signing_key)
    request = rdf_client_action.ExecutePythonRequest(python_code=signed_blob)
    result = self.RunAction(standard.ExecutePython, request)[0]

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

    self.assertGreater(result.time_used, 0)
    self.assertEqual(result.return_val, "Done.\n")

  def testExecuteModifiedPython(self):
    """Test that rejects invalid ExecutePython action."""
    utils.TEST_VAL = "original"
    python_code = "utils.TEST_VAL = 'modified'"
    signed_blob = rdf_crypto.SignedBlob()
    signed_blob.Sign(python_code.encode("utf-8"), self.signing_key)

    # Modify the data so the signature does not match.
    signed_blob.data = b"utils.TEST_VAL = 'notmodified'"

    request = rdf_client_action.ExecutePythonRequest(python_code=signed_blob)

    # Should raise since the code has been modified.
    self.assertRaises(rdf_crypto.VerificationError, self.RunAction,
                      standard.ExecutePython, request)

    # Lets also adjust the hash.
    signed_blob.digest = hashlib.sha256(signed_blob.data).digest()
    request = rdf_client_action.ExecutePythonRequest(python_code=signed_blob)

    self.assertRaises(rdf_crypto.VerificationError, self.RunAction,
                      standard.ExecutePython, request)

    # Make sure the code never ran.
    self.assertEqual(utils.TEST_VAL, "original")

  def testExecuteBrokenPython(self):
    """Test broken code raises back to the original flow."""
    python_code = "raise ValueError"
    signed_blob = rdf_crypto.SignedBlob()
    signed_blob.Sign(python_code.encode("utf-8"), self.signing_key)
    request = rdf_client_action.ExecutePythonRequest(python_code=signed_blob)

    self.assertRaises(ValueError, self.RunAction, standard.ExecutePython,
                      request)

  def testExecuteBinary(self):
    """Test the basic ExecuteBinaryCommand action."""
    signed_blob = rdf_crypto.SignedBlob()
    signed_blob.Sign(open("/bin/ls", "rb").read(), self.signing_key)

    request = rdf_client_action.ExecuteBinaryRequest(
        executable=signed_blob, args=[__file__], write_path="ablob")

    result = self.RunAction(standard.ExecuteBinaryCommand, request)[0]

    self.assertGreater(result.time_used, 0)
    self.assertIn(__file__, result.stdout)

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
    self.assertRaises(rdf_crypto.VerificationError, self.RunAction,
                      standard.ExecutePython, request)

  def testArgs(self):
    """Test passing arguments."""
    utils.TEST_VAL = "original"
    python_code = """
magic_return_str = py_args['test']
utils.TEST_VAL = py_args[43]
"""
    signed_blob = rdf_crypto.SignedBlob()
    signed_blob.Sign(python_code.encode("utf-8"), self.signing_key)
    pdict = rdf_protodict.Dict({"test": "dict_arg", 43: "dict_arg2"})
    request = rdf_client_action.ExecutePythonRequest(
        python_code=signed_blob, py_args=pdict)
    result = self.RunAction(standard.ExecutePython, request)[0]
    self.assertEqual(result.return_val, "dict_arg")
    self.assertEqual(utils.TEST_VAL, "dict_arg2")


class TestCopyPathToFile(client_test_lib.EmptyActionTest):
  """Test CopyPathToFile client actions."""

  def setUp(self):
    super(TestCopyPathToFile, self).setUp()
    self.path_in = os.path.join(self.base_path, "morenumbers.txt")
    self.hash_in = hashlib.sha1(open(self.path_in, "rb").read()).hexdigest()
    self.pathspec = rdf_paths.PathSpec(
        path=self.path_in, pathtype=rdf_paths.PathSpec.PathType.OS)

  def testCopyPathToFile(self):
    request = rdf_client_action.CopyPathToFileRequest(
        offset=0, length=0, src_path=self.pathspec, gzip_output=False)
    result = self.RunAction(standard.CopyPathToFile, request)[0]
    hash_out = hashlib.sha1(open(result.dest_path.path,
                                 "rb").read()).hexdigest()
    self.assertEqual(self.hash_in, hash_out)

  def testCopyPathToFileLimitLength(self):
    request = rdf_client_action.CopyPathToFileRequest(
        offset=0, length=23, src_path=self.pathspec, gzip_output=False)
    result = self.RunAction(standard.CopyPathToFile, request)[0]
    output = open(result.dest_path.path, "rb").read()
    self.assertLen(output, 23)

  def testCopyPathToFileOffsetandLimit(self):

    with open(self.path_in, "rb") as f:
      f.seek(38)
      out = f.read(25)
      hash_in = hashlib.sha1(out).hexdigest()

    request = rdf_client_action.CopyPathToFileRequest(
        offset=38, length=25, src_path=self.pathspec, gzip_output=False)
    result = self.RunAction(standard.CopyPathToFile, request)[0]
    output = open(result.dest_path.path, "rb").read()
    self.assertLen(output, 25)
    hash_out = hashlib.sha1(output).hexdigest()
    self.assertEqual(hash_in, hash_out)

  def testCopyPathToFileGzip(self):
    request = rdf_client_action.CopyPathToFileRequest(
        offset=0, length=0, src_path=self.pathspec, gzip_output=True)
    result = self.RunAction(standard.CopyPathToFile, request)[0]
    self.assertEqual(
        hashlib.sha1(gzip.open(result.dest_path.path).read()).hexdigest(),
        self.hash_in)

  def testCopyPathToFileLifetimeLimit(self):
    request = rdf_client_action.CopyPathToFileRequest(
        offset=0,
        length=23,
        src_path=self.pathspec,
        gzip_output=False,
        lifetime=0.1)
    result = self.RunAction(standard.CopyPathToFile, request)[0]
    self.assertTrue(os.path.exists(result.dest_path.path))
    time.sleep(1)
    self.assertFalse(os.path.exists(result.dest_path.path))


class GetFileStatTest(client_test_lib.EmptyActionTest):

  def testStatSize(self):
    with temp.AutoTempFilePath() as temp_filepath:
      with open(temp_filepath, "wb") as temp_file:
        temp_file.write("123456")

      pathspec = rdf_paths.PathSpec(
          path=temp_filepath, pathtype=rdf_paths.PathSpec.PathType.OS)

      request = rdf_client_action.GetFileStatRequest(pathspec=pathspec)
      results = self.RunAction(standard.GetFileStat, request)

      self.assertLen(results, 1)
      self.assertEqual(results[0].st_size, 6)

  def testStatExtAttrsEnabled(self):
    with temp.AutoTempFilePath() as temp_filepath:
      client_test_lib.SetExtAttr(temp_filepath, name="user.foo", value="bar")

      pathspec = rdf_paths.PathSpec(
          path=temp_filepath, pathtype=rdf_paths.PathSpec.PathType.OS)

      request = rdf_client_action.GetFileStatRequest(
          pathspec=pathspec, collect_ext_attrs=True)
      results = self.RunAction(standard.GetFileStat, request)

      self.assertLen(results, 1)
      self.assertLen(results[0].ext_attrs, 1)
      self.assertEqual(results[0].ext_attrs[0].name, "user.foo")
      self.assertEqual(results[0].ext_attrs[0].value, "bar")

  def testStatExtAttrsDisabled(self):
    with temp.AutoTempFilePath() as temp_filepath:
      client_test_lib.SetExtAttr(temp_filepath, name="user.foo", value="bar")

      pathspec = rdf_paths.PathSpec(
          path=temp_filepath, pathtype=rdf_paths.PathSpec.PathType.OS)

      request = rdf_client_action.GetFileStatRequest(
          pathspec=pathspec, collect_ext_attrs=False)
      results = self.RunAction(standard.GetFileStat, request)

      self.assertLen(results, 1)
      self.assertEmpty(results[0].ext_attrs)


class TestNetworkByteLimits(client_test_lib.EmptyActionTest):
  """Test CopyPathToFile client actions."""

  def setUp(self):
    super(TestNetworkByteLimits, self).setUp()
    pathspec = rdf_paths.PathSpec(
        path="/nothing", pathtype=rdf_paths.PathSpec.PathType.OS)
    self.buffer_ref = rdf_client.BufferReference(pathspec=pathspec, length=5000)
    self.data = "X" * 500
    self.old_read = standard.vfs.ReadVFS
    standard.vfs.ReadVFS = lambda x, y, z, progress_callback=None: self.data
    self.transfer_buf = action_mocks.ActionMock(standard.TransferBuffer)

  def testTransferNetworkByteLimitError(self):
    message = rdf_flows.GrrMessage(
        name="TransferBuffer",
        payload=self.buffer_ref,
        network_bytes_limit=300,
        generate_task_id=True)

    # We just get a client alert and a status message back.
    responses = self.transfer_buf.HandleMessage(message)

    client_alert = responses[0].payload
    self.assertIn("Network limit exceeded", str(client_alert))

    status = responses[1].payload
    self.assertTrue(
        "Action exceeded network send limit" in str(status.backtrace))
    self.assertEqual(status.status,
                     rdf_flows.GrrStatus.ReturnedStatus.NETWORK_LIMIT_EXCEEDED)

  def testTransferNetworkByteLimit(self):
    message = rdf_flows.GrrMessage(
        name="TransferBuffer",
        payload=self.buffer_ref,
        network_bytes_limit=900,
        generate_task_id=True)

    responses = self.transfer_buf.HandleMessage(message)

    for response in responses:
      if isinstance(response, rdf_flows.GrrStatus):
        self.assertEqual(response.payload.status,
                         rdf_flows.GrrStatus.ReturnedStatus.OK)

  def tearDown(self):
    super(TestNetworkByteLimits, self).tearDown()
    standard.vfs.ReadVFS = self.old_read


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
