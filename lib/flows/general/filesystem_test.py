#!/usr/bin/env python

# Copyright 2011 Google Inc.
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

"""Test the filesystem related flows."""

import os

from grr.lib import aff4
from grr.lib import test_lib
from grr.lib import utils
from grr.proto import jobs_pb2


class TestFilesystem(test_lib.FlowTestsBaseclass):
  """Test the interrogate flow."""

  def testListDirectory(self):
    """Test that the Find flow works."""
    client_mock = test_lib.ActionMock("ListDirectory")
    # Deliberately specify incorrect casing
    path = os.path.join(self.base_path, "test_img.dd",
                        "test directory")
    for _ in test_lib.TestFlowHelper(
        "ListDirectory", client_mock, client_id=self.client_id,
        path=path, pathtype=jobs_pb2.Path.TSK):
      pass

    # Check the output file is created
    output_path = aff4.ROOT_URN.Add(self.client_id).Add(
        "fs/raw").Add(self.base_path).Add("test_img.dd")

    fd = aff4.FACTORY.Open(output_path)
    children = list(fd.OpenChildren())
    self.assertEqual(len(children), 1)
    child = children[0]
    # Check that the object is stored with the correct casing.
    self.assertEqual(
        os.path.basename(utils.SmartUnicode(child.urn)), "Test Directory")

    # And the wrong object is not there
    self.assertRaises(IOError, aff4.FACTORY.Open,
                      output_path.Add("test directory"))

    aff4.FACTORY.Open(output_path.Add("Test Directory"))

  def testGetFile(self):
    """Test that the Find flow works."""
    client_mock = test_lib.ActionMock("ReadBuffer", "HashFile", "StatFile")
    # Deliberately specify incorrect casing
    path = os.path.join(self.base_path, "test_img.dd",
                        "test directory", "NumBers.txt")

    for _ in test_lib.TestFlowHelper(
        "GetFile", client_mock, client_id=self.client_id,
        path=path, pathtype=jobs_pb2.Path.TSK):
      pass

    # Check the output file is created
    output_path = aff4.ROOT_URN.Add(self.client_id).Add(
        "fs/raw").Add(self.base_path).Add("test_img.dd").Add(
            "Test Directory").Add("numbers.txt")

    fd = aff4.FACTORY.Open(output_path)
    self.assertEqual(fd.Read(10), "1\n2\n3\n4\n5\n")
    self.assertEqual(fd.size, 3893)

    # And the wrong object is not there
    self.assertRaises(IOError, aff4.FACTORY.Open, aff4.ROOT_URN.Add(
        self.client_id).Add(path))
