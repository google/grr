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

from grr.client import client_utils_linux
from grr.lib import aff4
from grr.lib import test_lib
from grr.proto import jobs_pb2


class TestChromePlugins(test_lib.FlowTestsBaseclass):
  """Test the chrome extension flow."""

  def testGetExtension(self):
    """Test that finding the Chrome plugin works."""

    # Set up client info
    self.client = aff4.FACTORY.Open(self.client_id)

    self.client.Set(self.client.Schema.SYSTEM,
                    aff4.RDFString("Linux"))

    user_list = self.client.Schema.USER()

    for u in [jobs_pb2.UserAccount(username="Foo",
                                   full_name="FooFoo",
                                   last_logon=150),
              jobs_pb2.UserAccount(username="test",
                                   full_name="test user",
                                   homedir="/home/test/",
                                   last_logon=250)]:
      user_list.Append(u)

    self.client.AddAttribute(self.client.Schema.USER, user_list)

    self.client.Close()

    client_mock = test_lib.ActionMock("ReadBuffer", "HashFile",
                                      "StatFile", "ListDirectory")

    def MockGetMountpoints():
      return {os.path.join(self.base_path, "test_img.dd"): "/"}

    client_utils_linux.LinSplitPathspec.func_defaults = (MockGetMountpoints,)

    # Run the flow in the simulated way
    for _ in test_lib.TestFlowHelper("ChromePlugins", client_mock,
                                     client_id=self.client_id, username="test",
                                     download_files=True, raw=True):
      pass

    client_utils_linux.LinSplitPathspec.func_defaults = (
        client_utils_linux.GetMountpoints,)

    fs_path = ("/home/test/.config/google-chrome/Default/Extensions/"
               "nlbjncdgjeocebhnmkbbbdekmmmcbfjd/2.1.3_0")

    # Check if the output VFile is created
    output_path = aff4.ROOT_URN.Add(self.client_id).Add(
        "fs/raw").Add(self.base_path).Add("test_img.dd").Add(fs_path)

    fd = aff4.FACTORY.Open(output_path)
    children = list(fd.OpenChildren())
    self.assertEqual(len(children), 3)

    # Check for Analysis dir
    output_path = aff4.ROOT_URN.Add(self.client_id).Add(
        "Analysis/Applications/Chrome/Extensions/"
        "RSS Subscription Extension (by Google)/2.1.3")

    fd = aff4.FACTORY.Open(output_path)

    self.assertEqual(fd.Get(fd.Schema.NAME),
                     "RSS Subscription Extension (by Google)")
    self.assertEqual(fd.Get(fd.Schema.VERSION),
                     "2.1.3")
    self.assertEqual(fd.Get(fd.Schema.CHROMEID),
                     "nlbjncdgjeocebhnmkbbbdekmmmcbfjd")
    self.assertEqual(fd.Get(fd.Schema.EXTENSIONDIR),
                     fs_path)

    # check for file downloads
    urns = [str(c.urn) for c in children if "testfile.txt" in str(c.urn)]

    self.assertEqual(len(urns), 1)

    fd = aff4.FACTORY.Open(urns[0])
    expect = "This should be downloaded automatically."
    self.assertTrue(fd.Read(10000).startswith(expect))
    self.assertEqual(fd.size, 41)
