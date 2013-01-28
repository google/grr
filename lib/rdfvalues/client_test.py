#!/usr/bin/env python
# -*- coding: utf-8 -*-
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


"""Client specific rdfvalue tests."""


import hashlib

from grr.lib import config_lib
from grr.lib import rdfvalue
from grr.lib.rdfvalues import test_base


CONFIG = config_lib.CONFIG


class SignedBlobTest(test_base.RDFValueTestCase):
  rdfvalue_class = rdfvalue.SignedBlob

  def setUp(self):
    super(SignedBlobTest, self).setUp()
    self.private_key = CONFIG["ClientSigningKeys.Driver_Signing_Private_Key"]
    self.public_key = CONFIG["ClientSigningKeys.Driver_Signing_Public_Key"]

  def GenerateSample(self, number=0):
    result = self.rdfvalue_class()
    result.Sign("Sample %s" % number, self.private_key)

    return result

  def testSignVerify(self):
    sample = self.GenerateSample()

    self.assertTrue(sample.Verify(self.public_key))

    # Change the data - this should fail since the hash is incorrect.
    sample.data += "X"
    self.assertFalse(sample.Verify(self.public_key))

    # Update the hash
    sample.digest = hashlib.sha256(sample.data).digest()

    # Should still fail.
    self.assertFalse(sample.Verify(self.public_key))

    # If we change the digest verification should fail.
    sample = self.GenerateSample()
    sample.digest_type = 555

    self.assertFalse(sample.Verify(self.public_key))
