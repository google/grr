#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

# Copyright 2012 Google Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Test client standard actions."""


from M2Crypto import RSA

from grr.client import conf as flags

from grr.lib import config_lib
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib import utils


FLAGS = flags.FLAGS
CONFIG = config_lib.CONFIG


class TestExecutePython(test_lib.EmptyActionTest):
  """Test the client execute actions."""

  def setUp(self):
    super(TestExecutePython, self).setUp()
    key_name = "ClientSigningKeys.executable_signing_private_key"
    self.signing_key = CONFIG[key_name]
    FLAGS.camode = "TEST"

  def testExecute(self):
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
    self.assertRaises(OSError, self.RunAction, "ExecutePython", request)

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
