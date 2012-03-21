#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

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
    """Test that the ListDirectory flow works."""
    client_mock = test_lib.ActionMock("ListDirectory", "StatFile")
    # Deliberately specify incorrect casing
    path = os.path.join(self.base_path, "test_img.dd")
    pb2 = jobs_pb2.Path(path="test directory",
                        pathtype=jobs_pb2.Path.TSK)
    pb = jobs_pb2.Path(path=path,
                       pathtype=jobs_pb2.Path.OS,
                       nested_path=pb2)
    for _ in test_lib.TestFlowHelper(
        "ListDirectory", client_mock, client_id=self.client_id,
        pathspec=pb, token=self.token):
      pass

    # Check the output file is created
    output_path = aff4.ROOT_URN.Add(self.client_id).Add(
        "fs/tsk").Add(path.replace("\\", "/"))

    fd = aff4.FACTORY.Open(output_path, token=self.token)
    children = list(fd.OpenChildren())
    self.assertEqual(len(children), 1)
    child = children[0]
    # Check that the object is stored with the correct casing.
    self.assertEqual(
        os.path.basename(utils.SmartUnicode(child.urn)), "Test Directory")

    # And the wrong object is not there
    self.assertRaises(IOError, fd.OpenMember,
                      output_path.Add("test directory"))

    # This directory does exist
    aff4.FACTORY.Open(output_path.Add("Test Directory"), token=self.token)

  def testUnicodeListDirectory(self):
    """Test that the ListDirectory flow works on unicode directories."""

    client_mock = test_lib.ActionMock("ListDirectory", "StatFile")
    # Deliberately specify incorrect casing
    path = os.path.join(self.base_path, "test_img.dd")
    pb2 = jobs_pb2.Path(path=u"入乡随俗 海外春节别样过法",
                        pathtype=jobs_pb2.Path.TSK)
    pb = jobs_pb2.Path(path=path,
                       pathtype=jobs_pb2.Path.OS,
                       nested_path=pb2)
    for _ in test_lib.TestFlowHelper(
        "ListDirectory", client_mock, client_id=self.client_id,
        pathspec=pb, token=self.token):
      pass

    # Check the output file is created
    output_path = aff4.ROOT_URN.Add(self.client_id).Add(
        "fs/tsk").Add(path.replace("\\", "/")).Add(pb2.path.replace("\\", "/"))

    fd = aff4.FACTORY.Open(output_path, token=self.token)
    children = list(fd.OpenChildren())
    self.assertEqual(len(children), 1)
    child = children[0]
    self.assertEqual(
        os.path.basename(utils.SmartUnicode(child.urn)), u"入乡随俗.txt")

  def testSlowGetFile(self):
    """Test that the SlowGetFile flow works."""
    client_mock = test_lib.ActionMock("ReadBuffer", "HashFile", "StatFile")
    # Deliberately specify incorrect casing
    path = os.path.join(self.base_path, "test_img.dd")
    pb2 = jobs_pb2.Path(path="test directory/NumBers.txt",
                        pathtype=jobs_pb2.Path.TSK)
    pb = jobs_pb2.Path(path=path,
                       pathtype=jobs_pb2.Path.OS,
                       nested_path=pb2)

    for _ in test_lib.TestFlowHelper(
        "SlowGetFile", client_mock, client_id=self.client_id,
        pathspec=pb, token=self.token):
      pass
    # Check the output file is created
    output_path = aff4.ROOT_URN.Add(self.client_id).Add(
        "fs/tsk").Add(path.replace("\\", "/")).Add(
            "Test Directory").Add("numbers.txt")

    fd = aff4.FACTORY.Open(output_path, token=self.token)
    self.assertEqual(fd.Read(10), "1\n2\n3\n4\n5\n")
    self.assertEqual(fd.size, 3893)

    # And the wrong object is not there
    client = aff4.FACTORY.Open(self.client_id, token=self.token)
    self.assertRaises(IOError, client.OpenMember, path)
