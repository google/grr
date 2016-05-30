#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

# Copyright 2012 Google Inc. All Rights Reserved.
"""Test client standard actions."""
import gzip
import hashlib
import os
import time


from grr.client.client_actions import standard
from grr.lib import action_mocks
from grr.lib import config_lib
from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib import utils
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import crypto as rdf_crypto
from grr.lib.rdfvalues import flows as rdf_flows
from grr.lib.rdfvalues import paths as rdf_paths
from grr.lib.rdfvalues import protodict as rdf_protodict


class TestExecutePython(test_lib.EmptyActionTest):
  """Test the client execute actions."""

  def setUp(self):
    super(TestExecutePython, self).setUp()
    self.signing_key = config_lib.CONFIG[
        "PrivateKeys.executable_signing_private_key"]

  def testExecutePython(self):
    """Test the basic ExecutePython action."""
    utils.TEST_VAL = "original"
    python_code = "utils.TEST_VAL = 'modified'"
    signed_blob = rdf_crypto.SignedBlob()
    signed_blob.Sign(python_code, self.signing_key)
    request = rdf_client.ExecutePythonRequest(python_code=signed_blob)
    result = self.RunAction("ExecutePython", request)[0]

    self.assertTrue(result.time_used > 0)
    self.assertEqual(result.return_val, "")
    self.assertEqual(utils.TEST_VAL, "modified")

  def testExecutePythonEnvironment(self):
    """Test the basic ExecutePython action."""

    python_code = """
import StringIO
import uu

def decode(encoded):
  # Use the import (uu) inside a function. This will fail if the environment
  # for exec is not set up properly.
  i = StringIO.StringIO(s)
  o = StringIO.StringIO()
  uu.decode(i, o)
  return o.getvalue()

s = "626567696e20363636202d0a2c3226354c3b265c4035565d523b2630410a200a656e640a"
s = s.decode("hex")

magic_return_str = decode(s)
"""
    signed_blob = rdf_crypto.SignedBlob()
    signed_blob.Sign(python_code, self.signing_key)
    request = rdf_client.ExecutePythonRequest(python_code=signed_blob)
    result = self.RunAction("ExecutePython", request)[0]

    self.assertTrue(result.time_used > 0)
    self.assertEqual(result.return_val, "Hello World!")

  def testStdoutHooking(self):
    python_code = """

def f(n):
    print "F called:", n

print "Calling f."
f(1)
print "Done."
"""
    signed_blob = rdf_crypto.SignedBlob()
    signed_blob.Sign(python_code, self.signing_key)
    request = rdf_client.ExecutePythonRequest(python_code=signed_blob)
    result = self.RunAction("ExecutePython", request)[0]

    self.assertTrue(result.time_used > 0)
    self.assertEqual(result.return_val, "Calling f.\nF called: 1\nDone.\n")

  def testProgress(self):
    python_code = """

def f():
    # This should also work inside a function.
    Progress()

f()
Progress()
print "Done."
"""
    signed_blob = rdf_crypto.SignedBlob()
    signed_blob.Sign(python_code, self.signing_key)
    request = rdf_client.ExecutePythonRequest(python_code=signed_blob)
    result = self.RunAction("ExecutePython", request)[0]

    self.assertTrue(result.time_used > 0)
    self.assertEqual(result.return_val, "Done.\n")

  def testExecuteModifiedPython(self):
    """Test that rejects invalid ExecutePython action."""
    utils.TEST_VAL = "original"
    python_code = "utils.TEST_VAL = 'modified'"
    signed_blob = rdf_crypto.SignedBlob()
    signed_blob.Sign(python_code, self.signing_key)

    # Modify the data so the signature does not match.
    signed_blob.data = "utils.TEST_VAL = 'notmodified'"

    request = rdf_client.ExecutePythonRequest(python_code=signed_blob)

    # Should raise since the code has been modified.
    self.assertRaises(rdfvalue.DecodeError, self.RunAction, "ExecutePython",
                      request)

    # Lets also adjust the hash.
    signed_blob.digest = hashlib.sha256(signed_blob.data).digest()
    request = rdf_client.ExecutePythonRequest(python_code=signed_blob)

    self.assertRaises(rdfvalue.DecodeError, self.RunAction, "ExecutePython",
                      request)

    # Make sure the code never ran.
    self.assertEqual(utils.TEST_VAL, "original")

  def testExecuteBrokenPython(self):
    """Test broken code raises back to the original flow."""
    python_code = "raise ValueError"
    signed_blob = rdf_crypto.SignedBlob()
    signed_blob.Sign(python_code, self.signing_key)
    request = rdf_client.ExecutePythonRequest(python_code=signed_blob)

    self.assertRaises(ValueError, self.RunAction, "ExecutePython", request)

  def testExecuteBinary(self):
    """Test the basic ExecuteBinaryCommand action."""
    signed_blob = rdf_crypto.SignedBlob()
    signed_blob.Sign(open("/bin/ls").read(), self.signing_key)

    writefile = utils.Join(self.temp_dir, "binexecute", "ablob")
    os.makedirs(os.path.dirname(writefile))
    request = rdf_client.ExecuteBinaryRequest(executable=signed_blob,
                                              args=[__file__],
                                              write_path=writefile)

    result = self.RunAction("ExecuteBinaryCommand", request)[0]

    self.assertTrue(result.time_used > 0)
    self.assertTrue(__file__ in result.stdout)

  def testReturnVals(self):
    """Test return values."""
    python_code = "magic_return_str = 'return string'"
    signed_blob = rdf_crypto.SignedBlob()
    signed_blob.Sign(python_code, self.signing_key)
    request = rdf_client.ExecutePythonRequest(python_code=signed_blob)
    result = self.RunAction("ExecutePython", request)[0]

    self.assertEqual(result.return_val, "return string")

  def testWrongKey(self):
    """Test return values."""
    python_code = "print 'test'"

    # Generate a test valid RSA key that isn't the real one.
    signing_key = rdf_crypto.PEMPrivateKey.GenKey(2048, 65537)
    signed_blob = rdf_crypto.SignedBlob()
    signed_blob.Sign(python_code, signing_key)
    request = rdf_client.ExecutePythonRequest(python_code=signed_blob)
    self.assertRaises(rdfvalue.DecodeError, self.RunAction, "ExecutePython",
                      request)

  def testArgs(self):
    """Test passing arguments."""
    utils.TEST_VAL = "original"
    python_code = """
magic_return_str = py_args['test']
utils.TEST_VAL = py_args[43]
"""
    signed_blob = rdf_crypto.SignedBlob()
    signed_blob.Sign(python_code, self.signing_key)
    pdict = rdf_protodict.Dict({"test": "dict_arg", 43: "dict_arg2"})
    request = rdf_client.ExecutePythonRequest(python_code=signed_blob,
                                              py_args=pdict)
    result = self.RunAction("ExecutePython", request)[0]
    self.assertEqual(result.return_val, "dict_arg")
    self.assertEqual(utils.TEST_VAL, "dict_arg2")


class TestCopyPathToFile(test_lib.EmptyActionTest):
  """Test CopyPathToFile client actions."""

  def setUp(self):
    super(TestCopyPathToFile, self).setUp()
    self.path_in = os.path.join(self.base_path, "morenumbers.txt")
    self.hash_in = hashlib.sha1(open(self.path_in).read()).hexdigest()
    self.pathspec = rdf_paths.PathSpec(path=self.path_in,
                                       pathtype=rdf_paths.PathSpec.PathType.OS)

  def testCopyPathToFile(self):
    request = rdf_client.CopyPathToFileRequest(offset=0,
                                               length=0,
                                               src_path=self.pathspec,
                                               dest_dir=self.temp_dir,
                                               gzip_output=False)
    result = self.RunAction("CopyPathToFile", request)[0]
    hash_out = hashlib.sha1(open(result.dest_path.path).read()).hexdigest()
    self.assertEqual(self.hash_in, hash_out)

  def testCopyPathToFileLimitLength(self):
    request = rdf_client.CopyPathToFileRequest(offset=0,
                                               length=23,
                                               src_path=self.pathspec,
                                               dest_dir=self.temp_dir,
                                               gzip_output=False)
    result = self.RunAction("CopyPathToFile", request)[0]
    output = open(result.dest_path.path).read()
    self.assertEqual(len(output), 23)

  def testCopyPathToFileOffsetandLimit(self):

    with open(self.path_in) as f:
      f.seek(38)
      out = f.read(25)
      hash_in = hashlib.sha1(out).hexdigest()

    request = rdf_client.CopyPathToFileRequest(offset=38,
                                               length=25,
                                               src_path=self.pathspec,
                                               dest_dir=self.temp_dir,
                                               gzip_output=False)
    result = self.RunAction("CopyPathToFile", request)[0]
    output = open(result.dest_path.path).read()
    self.assertEqual(len(output), 25)
    hash_out = hashlib.sha1(output).hexdigest()
    self.assertEqual(hash_in, hash_out)

  def testCopyPathToFileGzip(self):
    request = rdf_client.CopyPathToFileRequest(offset=0,
                                               length=0,
                                               src_path=self.pathspec,
                                               dest_dir=self.temp_dir,
                                               gzip_output=True)
    result = self.RunAction("CopyPathToFile", request)[0]
    self.assertEqual(
        hashlib.sha1(gzip.open(result.dest_path.path).read()).hexdigest(),
        self.hash_in)

  def testCopyPathToFileLifetimeLimit(self):
    request = rdf_client.CopyPathToFileRequest(offset=0,
                                               length=23,
                                               src_path=self.pathspec,
                                               dest_dir=self.temp_dir,
                                               gzip_output=False,
                                               lifetime=0.1)
    result = self.RunAction("CopyPathToFile", request)[0]
    self.assertTrue(os.path.exists(result.dest_path.path))
    time.sleep(1)
    self.assertFalse(os.path.exists(result.dest_path.path))


class TestNetworkByteLimits(test_lib.EmptyActionTest):
  """Test CopyPathToFile client actions."""

  def setUp(self):
    super(TestNetworkByteLimits, self).setUp()
    pathspec = rdf_paths.PathSpec(path="/nothing",
                                  pathtype=rdf_paths.PathSpec.PathType.OS)
    self.buffer_ref = rdf_client.BufferReference(pathspec=pathspec, length=5000)
    self.data = "X" * 500
    self.old_read = standard.vfs.ReadVFS
    standard.vfs.ReadVFS = lambda x, y, z, progress_callback=None: self.data
    self.transfer_buf = action_mocks.ActionMock("TransferBuffer")

  def testTransferNetworkByteLimitError(self):
    message = rdf_flows.GrrMessage(name="TransferBuffer",
                                   payload=self.buffer_ref,
                                   network_bytes_limit=300)

    # We just get a client alert and a status message back.
    responses = self.transfer_buf.HandleMessage(message)

    client_alert = responses[0].payload
    self.assertTrue("Network limit exceeded" in str(client_alert))

    status = responses[1].payload
    self.assertTrue("Action exceeded network send limit" in str(
        status.backtrace))
    self.assertEqual(status.status,
                     rdf_flows.GrrStatus.ReturnedStatus.NETWORK_LIMIT_EXCEEDED)

  def testTransferNetworkByteLimit(self):
    message = rdf_flows.GrrMessage(name="TransferBuffer",
                                   payload=self.buffer_ref,
                                   network_bytes_limit=900)

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
