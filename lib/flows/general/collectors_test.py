#!/usr/bin/env python
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


"""Test the collector flows."""


import os

from grr.client import conf as flags

from grr.lib import aff4
from grr.lib import artifact
from grr.lib import test_lib

FLAGS = flags.FLAGS


class FakeArtifact(artifact.GenericArtifact):
  """My first artifact."""
  SUPPORTED_OS = ["Linux"]
  LABELS = ["Logs", "Auth"]
  COLLECTORS = []
  PATH_VARS = {}


class TestArtifactCollectors(test_lib.FlowTestsBaseclass):
  """Test the artifact collection mechanism works."""

  def tearDown(self):
    super(TestArtifactCollectors, self).tearDown()
    FakeArtifact.COLLECTORS = []  # Reset any Collectors
    FakeArtifact.CONDITIONS = []  # Reset any Conditions

  def testGetArtifact1(self):
    """Test we can get a basic artifact."""
    client_mock = test_lib.ActionMock("TransferBuffer", "StatFile")
    client = aff4.FACTORY.Open(self.client_id, token=self.token, mode="rw")
    client.Set(client.Schema.SYSTEM("Linux"))
    client.Flush()

    # Dynamically add a Collector specifying the base path.
    file_path = os.path.join(self.base_path, "test_img.dd")
    coll1 = artifact.Collector(action="GetFile", args={"path": file_path})
    FakeArtifact.COLLECTORS.append(coll1)
    artifact_list = ["FakeArtifact"]
    for _ in test_lib.TestFlowHelper("ArtifactCollectorFlow", client_mock,
                                     artifact_list=artifact_list, use_tsk=False,
                                     token=self.token, client_id=self.client_id
                                    ):
      pass

    # Test the AFF4 file that was created.
    fd1 = aff4.FACTORY.Open("%s/fs/os/%s" % (self.client_id, file_path),
                            token=self.token)
    fd2 = open(file_path)
    fd2.seek(0, 2)

    self.assertEqual(fd2.tell(), int(fd1.Get(fd1.Schema.SIZE)))
