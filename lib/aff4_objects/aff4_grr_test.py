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

"""Test the grr aff4 objects."""


from grr.lib import aff4
from grr.lib import test_lib
from grr.lib import utils

from grr.proto import jobs_pb2


class AFF4GRRTest(test_lib.AFF4ObjectTest):
  """Test the client aff4 implementation."""

  def testPathspecToURN(self):
    """Test the pathspec to URN conversion function."""
    pathspec = utils.Pathspec(
        path="\\\\.\\Volume{1234}\\", pathtype=jobs_pb2.Path.OS,
        mount_point="/c:/").Append(
            path="/windows",
            pathtype=jobs_pb2.Path.TSK)

    urn = aff4.AFF4Object.VFSGRRClient.PathspecToURN(pathspec, "C.1234")
    self.assertEqual(
        urn, aff4.RDFURN(r"aff4:/C.1234/fs/tsk/\\.\Volume{1234}\/windows"))

    # Test an ADS
    pathspec = utils.Pathspec(
        path="\\\\.\\Volume{1234}\\", pathtype=jobs_pb2.Path.OS,
        mount_point="/c:/").Append(
            pathtype=jobs_pb2.Path.TSK,
            path="/Test Directory/notes.txt:ads",
            inode=66,
            ntfs_type=128,
            ntfs_id=2)

    urn = aff4.AFF4Object.VFSGRRClient.PathspecToURN(pathspec, "C.1234")
    self.assertEqual(
        urn, aff4.RDFURN(r"aff4:/C.1234/fs/tsk/\\.\Volume{1234}\/"
                         "Test Directory/notes.txt:ads"))

  def testClientSubfieldGet(self):
    """Test we can get subfields of the client."""

    fd = aff4.FACTORY.Create("C.0000000000000000", "VFSGRRClient",
                             token=self.token, age=aff4.ALL_TIMES)

    for i in range(5):
      folder = "C:/Users/user%s" % i
      user_pb = jobs_pb2.UserAccount(username="user%s" % i)
      user_pb.special_folders.app_data = folder

      fd.AddAttribute(fd.Schema.USER(user_pb))

    fd.Close()

    # Check the repeated Users array.
    for i, folder in enumerate(
        fd.GetValuesForAttribute("Users.special_folders.app_data")):
      self.assertEqual(folder, "C:/Users/user%s" % i)
