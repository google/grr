#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

# Copyright 2012 Google Inc. All Rights Reserved.
"""Test client standard actions."""
import hashlib


from M2Crypto import RSA

from grr.lib import config_lib
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib import utils


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
    signed_blob = rdfvalue.SignedBlob()
    signed_blob.Sign(python_code, self.signing_key)
    request = rdfvalue.ExecutePythonRequest(python_code=signed_blob)
    result = self.RunAction("ExecutePython", request)[0]

    self.assertTrue(result.time_used > 0)
    self.assertEqual(result.return_val, "")
    self.assertEqual(utils.TEST_VAL, "modified")

  def testExecuteModifiedPython(self):
    """Test that rejects invalid ExecutePython action."""
    utils.TEST_VAL = "original"
    python_code = "utils.TEST_VAL = 'modified'"
    signed_blob = rdfvalue.SignedBlob()
    signed_blob.Sign(python_code, self.signing_key)

    # Modify the data so the signature does not match.
    signed_blob.data = "utils.TEST_VAL = 'notmodified'"

    request = rdfvalue.ExecutePythonRequest(python_code=signed_blob)

    # Should raise since the code has been modified.
    self.assertRaises(rdfvalue.DecodeError,
                      self.RunAction, "ExecutePython", request)

    # Lets also adjust the hash.
    signed_blob.digest = hashlib.sha256(signed_blob.data).digest()
    request = rdfvalue.ExecutePythonRequest(python_code=signed_blob)

    self.assertRaises(rdfvalue.DecodeError,
                      self.RunAction, "ExecutePython", request)

    # Make sure the code never ran.
    self.assertEqual(utils.TEST_VAL, "original")

  def testExecuteBinary(self):
    """Test the basic ExecuteBinaryCommand action."""
    signed_blob = rdfvalue.SignedBlob()
    signed_blob.Sign(open("/bin/ls").read(), self.signing_key)

    request = rdfvalue.ExecuteBinaryRequest(executable=signed_blob,
                                            args=[__file__])

    result = self.RunAction("ExecuteBinaryCommand", request)[0]

    self.assertTrue(result.time_used > 0)
    self.assertTrue(__file__ in result.stdout)

  def testReturnVals(self):
    """Test return values."""
    python_code = "magic_return_str = 'return string'"
    signed_blob = rdfvalue.SignedBlob()
    signed_blob.Sign(python_code, self.signing_key)
    request = rdfvalue.ExecutePythonRequest(python_code=signed_blob)
    result = self.RunAction("ExecutePython", request)[0]

    self.assertEqual(result.return_val, "return string")

  def testWrongKey(self):
    """Test return values."""
    python_code = "print 'test'"

    # Generate a test valid RSA key that isn't the real one.
    signing_key = RSA.gen_key(2048, 65537).as_pem(None)
    signed_blob = rdfvalue.SignedBlob()
    signed_blob.Sign(python_code, signing_key)
    request = rdfvalue.ExecutePythonRequest(python_code=signed_blob)
    self.assertRaises(rdfvalue.DecodeError, self.RunAction,
                      "ExecutePython", request)

  def testArgs(self):
    """Test passing arguments."""
    utils.TEST_VAL = "original"
    python_code = """
magic_return_str = py_args['test']
utils.TEST_VAL = py_args[43]
"""
    signed_blob = rdfvalue.SignedBlob()
    signed_blob.Sign(python_code, self.signing_key)
    pdict = rdfvalue.RDFProtoDict({"test": "dict_arg",
                                   43: "dict_arg2"})
    request = rdfvalue.ExecutePythonRequest(python_code=signed_blob,
                                            py_args=pdict)
    result = self.RunAction("ExecutePython", request)[0]
    self.assertEqual(result.return_val, "dict_arg")
    self.assertEqual(utils.TEST_VAL, "dict_arg2")
