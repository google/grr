#!/usr/bin/env python
"""Test the collector flows."""


import os

from grr.lib import aff4
from grr.lib import artifact
from grr.lib import artifact_lib
from grr.lib import rdfvalue
from grr.lib import test_lib


class FakeArtifact(artifact_lib.GenericArtifact):
  """My first artifact."""
  SUPPORTED_OS = ["Linux"]
  LABELS = ["Logs", "Authentication"]
  COLLECTORS = []
  PATH_VARS = {}


class TestArtifactCollectors(test_lib.FlowTestsBaseclass):
  """Test the artifact collection mechanism works."""

  def setUp(self):
    """Make sure things are initialized."""
    super(TestArtifactCollectors, self).setUp()
    with aff4.FACTORY.Open(self.client_id, token=self.token, mode="rw") as fd:
      fd.Set(fd.Schema.SYSTEM("Linux"))
      kb = fd.Schema.KNOWLEDGE_BASE()
      artifact.SetCoreGRRKnowledgeBaseValues(kb, fd)
      fd.Set(kb)

  def tearDown(self):
    super(TestArtifactCollectors, self).tearDown()
    FakeArtifact.COLLECTORS = []  # Reset any Collectors
    FakeArtifact.CONDITIONS = []  # Reset any Conditions

  def testGetArtifact1(self):
    """Test we can get a basic artifact."""
    client_mock = test_lib.ActionMock("TransferBuffer", "StatFile", "Find",
                                      "HashFile", "HashBuffer")
    client = aff4.FACTORY.Open(self.client_id, token=self.token, mode="rw")
    client.Set(client.Schema.SYSTEM("Linux"))
    client.Flush()

    # Dynamically add a Collector specifying the base path.
    file_path = os.path.join(self.base_path, "test_img.dd")
    coll1 = artifact_lib.Collector(action="GetFile", args={"path": file_path})
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

  def testRunGrrClientActionArtifact(self):
    """Test we can get a GRR client artifact."""
    client_mock = test_lib.ActionMock("ListProcesses")
    client = aff4.FACTORY.Open(self.client_id, token=self.token, mode="rw")
    client.Set(client.Schema.SYSTEM("Linux"))
    client.Flush()

    coll1 = artifact_lib.Collector(action="RunGrrClientAction",
                                   args={"client_action": r"ListProcesses"})
    FakeArtifact.COLLECTORS.append(coll1)
    artifact_list = ["FakeArtifact"]
    for _ in test_lib.TestFlowHelper("ArtifactCollectorFlow", client_mock,
                                     artifact_list=artifact_list,
                                     token=self.token, client_id=self.client_id,
                                     output="test_artifact"
                                    ):
      pass

    # Test the AFF4 file that was created.
    fd = aff4.FACTORY.Open(rdfvalue.RDFURN(self.client_id).Add("test_artifact"),
                           token=self.token)
    self.assertTrue(isinstance(list(fd)[0], rdfvalue.Process))
    self.assertTrue(len(fd) > 5)
