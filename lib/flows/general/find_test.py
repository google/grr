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

"""Tests for the Find flow."""
from grr.client import vfs
from grr.lib import aff4
from grr.lib import test_lib
from grr.lib import utils
from grr.lib.aff4_objects import standard
from grr.proto import jobs_pb2


class TestFindFlow(test_lib.FlowTestsBaseclass):
  """Test the interrogate flow."""

  def testFindFiles(self):
    """Test that the Find flow works with files."""
    # Install the mock
    vfs.VFS_HANDLERS[jobs_pb2.Path.OS] = test_lib.ClientVFSHandlerFixture

    client_mock = test_lib.ActionMock("Find")
    output_path = "analysis/FindFlowTest1"

    for _ in test_lib.TestFlowHelper(
        "FindFiles", client_mock, client_id=self.client_id,
        path="/", filename_regex="bash", token=self.token,
        pathtype=jobs_pb2.Path.OS, output=output_path):
      pass

    # Check the output file is created
    fd = aff4.FACTORY.Open("aff4:/{0}/{1}".format(self.client_id,
                                                  output_path),
                           token=self.token)

    # Make sure that bash is a file.
    children = list(fd.OpenChildren())
    self.assertEqual(len(children), 4)
    for child in children:
      path = utils.SmartStr(child.urn)
      self.assert_(path.endswith("bash"))
      self.assertEqual(child.__class__.__name__, "VFSFile")

  def testFindDirectories(self):
    """Test that the Find flow works with directories."""
    # Install the mock
    vfs.VFS_HANDLERS[jobs_pb2.Path.OS] = test_lib.ClientVFSHandlerFixture

    client_mock = test_lib.ActionMock("Find")
    output_path = "analysis/FindFlowTest2"

    for _ in test_lib.TestFlowHelper(
        "FindFiles", client_mock, client_id=self.client_id,
        path="/", filename_regex="bin", token=self.token,
        pathtype=jobs_pb2.Path.OS, output=output_path):
      pass

    # Check the output file is created
    fd = aff4.FACTORY.Open(
        "aff4:/{0}/{1}".format(self.client_id, output_path),
        token=self.token)

    # Make sure that bin is a directory
    children = list(fd.OpenChildren())
    self.assertEqual(len(children), 2)
    for child in children:
      path = utils.SmartStr(child.urn)
      self.assert_("bin" in path)
      self.assertEqual(child.__class__.__name__, "VFSDirectory")

  def testFindWithFindSpec(self):
    """Test that the Find flow works when specifying proto directly."""
    # Install the mock
    vfs.VFS_HANDLERS[jobs_pb2.Path.OS] = test_lib.ClientVFSHandlerFixture
    client_mock = test_lib.ActionMock("Find")

    # Additionally test the expansion of user variable.
    output_path = "analysis/FindFlowTest3.{u}"
    expected_output_path = output_path.replace("{u}", "test")

    pathspec = jobs_pb2.Path(path="/", pathtype=jobs_pb2.Path.OS)
    pb = jobs_pb2.Find(pathspec=pathspec, path_regex="bin")

    for _ in test_lib.TestFlowHelper(
        "FindFiles", client_mock, client_id=self.client_id,
        findspec=pb, output=output_path, token=self.token):
      pass

    # Check the output file is created
    fd = aff4.FACTORY.Open(
        "aff4:/{0}/{1}".format(self.client_id, expected_output_path),
        token=self.token)

    # Make sure that bin is a directory
    children = list(fd.OpenChildren())
    self.assertEqual(len(children), 2)
    for child in children:
      path = utils.SmartStr(child.urn)
      self.assert_("bin" in path)
      self.assertTrue(isinstance(child, standard.VFSDirectory))

  def testFindWithMaxFiles(self):
    """Test that the Find flow works when specifying proto directly."""
    # Install the mock
    vfs.VFS_HANDLERS[jobs_pb2.Path.OS] = test_lib.ClientVFSHandlerFixture
    client_mock = test_lib.ActionMock("Find")
    output_path = "analysis/FindFlowTest4"

    pathspec = jobs_pb2.Path(path="/", pathtype=jobs_pb2.Path.OS)
    pb = jobs_pb2.Find(pathspec=pathspec, path_regex=".*")

    for _ in test_lib.TestFlowHelper(
        "FindFiles", client_mock, client_id=self.client_id, token=self.token,
        findspec=pb, output=output_path, iterate_on_number=3, max_results=7):
      pass

    # Check the output file is created
    fd = aff4.FACTORY.Open(
        "aff4:/{0}/{1}".format(self.client_id, output_path),
        token=self.token)

    # Make sure we got the right number of results.
    children = list(fd.OpenChildren())
    self.assertEqual(len(children), 7)

  def testCollectionAddition(self):
    """Test we add to a collection instead of overwriting."""
    # Install the mock
    vfs.VFS_HANDLERS[jobs_pb2.Path.OS] = test_lib.ClientVFSHandlerFixture
    client_mock = test_lib.ActionMock("Find")
    output_path = "analysis/FindFlowTest5"
    pathspec = jobs_pb2.Path(path="/", pathtype=jobs_pb2.Path.OS)
    pb = jobs_pb2.Find(pathspec=pathspec, path_regex="bin")

    for _ in test_lib.TestFlowHelper(
        "FindFiles", client_mock, client_id=self.client_id, token=self.token,
        findspec=pb, output=output_path):
      pass

    output_path = "aff4:/{0}/{1}".format(self.client_id, output_path)
    # Check the output file with the right number of results.
    children = list(
        aff4.FACTORY.Open(output_path, token=self.token).OpenChildren())
    self.assertEqual(len(children), 2)

    # Now find the same results, should update, but not add to collection.
    for _ in test_lib.TestFlowHelper(
        "FindFiles", client_mock, client_id=self.client_id, token=self.token,
        findspec=pb, output=output_path):
      pass

    children = list(
        aff4.FACTORY.Open(output_path, token=self.token).OpenChildren())
    self.assertEqual(len(children), 2)

    # Now find a new result, should update.
    pb.path_regex = "dd"
    for _ in test_lib.TestFlowHelper(
        "FindFiles", client_mock, client_id=self.client_id, token=self.token,
        findspec=pb, output=output_path, max_results=1):
      pass

    children = list(aff4.FACTORY.Open(
        output_path, token=self.token).OpenChildren())
    self.assertEqual(len(children), 3)
