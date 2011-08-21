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

from google.protobuf import text_format
from grr.client import vfs
from grr.lib import aff4
from grr.lib import test_lib
from grr.lib import utils
from grr.proto import jobs_pb2
from grr.test_data import client_fixture


# This registers the mock as a handler for paths which begin with /fixture/
class MockVFSHandlerFindFlow(vfs.AbstractDirectoryHandler):
  """A mock VFS handler with fake files."""

  supported_pathtype = jobs_pb2.Path.OS
  paths = None
  altitude = 4
  prefix = "/fixture"

  def __init__(self, pathspec):
    path = pathspec.mountpoint + pathspec.path
    if not path.startswith(self.prefix):
      raise IOError("not mocking")
    self.path = path[len(self.prefix):]
    if not self.path:
      self.path = "/"

    # Parse the paths from the fixture
    self.paths = {}
    for path, (_, attributes) in client_fixture.VFS:
      if path.startswith("/fs/os"):
        path = path[len("/fs/os"):]
        if not path:
          path = "/"
      else:
        continue
      for attribute, value in attributes.items():
        if attribute == "aff4:directory_listing":
          directory_proto = jobs_pb2.DirectoryINode()
          text_format.Merge(utils.SmartStr(value), directory_proto)
          if directory_proto.children:
            for child in directory_proto.children:
              child.pathspec.CopyFrom(pathspec)
              child.pathspec.path = utils.JoinPath(pathspec.path, child.path)

            self.paths[path] = list(directory_proto.children)

  def ListFiles(self):
    result = self.paths.get(self.path)
    return result


class TestFindFlow(test_lib.FlowTestsBaseclass):
  """Test the interrogate flow."""

  def testFlow(self):
    """Test that the Find flow works."""
    client_mock = test_lib.ActionMock("Find")
    output_path = "aff4:/analysis/FindFlowTest"

    for _ in test_lib.TestFlowHelper(
        "FindFiles", client_mock, client_id=self.client_id,
        path="/fixture/", filename_regex="bash",
        raw=False, output=output_path):
      pass

    # Check the output file is created
    fd = aff4.FACTORY.Open(output_path)

    # Should have found bash and rbash
    children = list(fd.OpenChildren())
    self.assertEqual(len(children), 2)
    for child in children:
      path = utils.SmartStr(child.urn)
      self.assert_(path.endswith("bash"))
