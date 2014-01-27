#!/usr/bin/env python
"""Test the collector flows."""


import os
import random

from grr.client import vfs
from grr.lib import aff4
from grr.lib import artifact
from grr.lib import artifact_lib
from grr.lib import artifact_test
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib.flows.general import transfer


class TestArtifactCollectors(artifact_test.ArtifactTestHelper):
  """Test the artifact collection mechanism works."""

  def setUp(self):
    """Make sure things are initialized."""
    super(TestArtifactCollectors, self).setUp()

    self.LoadTestArtifacts()
    artifact_reg = artifact_lib.ArtifactRegistry.artifacts
    self.fakeartifact = artifact_reg["FakeArtifact"]
    self.badpathspecartifact = artifact_reg["BadPathspecArtifact"]

    with aff4.FACTORY.Open(self.client_id, token=self.token, mode="rw") as fd:
      fd.Set(fd.Schema.SYSTEM("Linux"))
      kb = fd.Schema.KNOWLEDGE_BASE()
      artifact.SetCoreGRRKnowledgeBaseValues(kb, fd)
      fd.Set(kb)

  def tearDown(self):
    super(TestArtifactCollectors, self).tearDown()
    self.fakeartifact.collectors = []  # Reset any Collectors
    self.fakeartifact.conditions = []  # Reset any Conditions

  def testGetArtifact1(self):
    """Test we can get a basic artifact."""

    client_mock = test_lib.ActionMock("TransferBuffer", "StatFile", "Find",
                                      "HashFile", "HashBuffer")
    client = aff4.FACTORY.Open(self.client_id, token=self.token, mode="rw")
    client.Set(client.Schema.SYSTEM("Linux"))
    client.Flush()

    # Dynamically add a Collector specifying the base path.
    file_path = os.path.join(self.base_path, "test_img.dd")
    coll1 = rdfvalue.Collector(action="GetFile", args={"path": file_path})
    self.fakeartifact.collectors.append(coll1)

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

    coll1 = rdfvalue.Collector(action="RunGrrClientAction",
                               args={"client_action": r"ListProcesses"})
    self.fakeartifact.collectors.append(coll1)
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

  def testConditions(self):
    """Test we can get a GRR client artifact with conditions."""
    # Run with false condition.
    client_mock = test_lib.ActionMock("ListProcesses")
    coll1 = rdfvalue.Collector(action="RunGrrClientAction",
                               args={"client_action": "ListProcesses"},
                               conditions=["os == 'Windows'"])
    self.fakeartifact.collectors.append(coll1)
    fd = self._RunClientActionArtifact(client_mock, ["FakeArtifact"])
    self.assertEquals(fd.__class__.__name__, "AFF4Volume")

    # Now run with matching or condition.
    coll1.conditions = ["os == 'Linux' or os == 'Windows'"]
    self.fakeartifact.collectors = []
    self.fakeartifact.collectors.append(coll1)
    fd = self._RunClientActionArtifact(client_mock, ["FakeArtifact"])
    self.assertEquals(fd.__class__.__name__, "RDFValueCollection")

    # Now run with impossible or condition.
    coll1.conditions.append("os == 'NotTrue'")
    self.fakeartifact.collectors = []
    self.fakeartifact.collectors.append(coll1)
    fd = self._RunClientActionArtifact(client_mock, ["FakeArtifact"])
    self.assertEquals(fd.__class__.__name__, "AFF4Volume")

  def _RunClientActionArtifact(self, client_mock, artifact_list):
    client = aff4.FACTORY.Open(self.client_id, token=self.token, mode="rw")
    client.Set(client.Schema.SYSTEM("Linux"))
    client.Flush()
    output = "test_artifact_%s" % random.randrange(1, 1000)
    for _ in test_lib.TestFlowHelper("ArtifactCollectorFlow", client_mock,
                                     artifact_list=artifact_list,
                                     token=self.token, client_id=self.client_id,
                                     output=output
                                    ):
      pass

    # Test the AFF4 file was not created, as flow should not have run due to
    # conditions.
    fd = aff4.FACTORY.Open(rdfvalue.RDFURN(self.client_id).Add(output),
                           token=self.token)
    return fd

  def testProcessCollectedArtifacts(self):
    """Test downloading files from artifacts."""
    client = aff4.FACTORY.Open(self.client_id, token=self.token, mode="rw")
    client.Set(client.Schema.SYSTEM("Windows"))
    client.Set(client.Schema.OS_VERSION("6.2"))
    client.Flush()

    vfs.VFS_HANDLERS[
        rdfvalue.PathSpec.PathType.REGISTRY] = test_lib.ClientRegistryVFSFixture
    vfs.VFS_HANDLERS[
        rdfvalue.PathSpec.PathType.OS] = test_lib.ClientFullVFSFixture

    client_mock = test_lib.ActionMock("TransferBuffer", "StatFile", "Find",
                                      "HashBuffer", "HashFile", "ListDirectory")

    # Add some user accounts to this client.
    fd = aff4.FACTORY.Open(self.client_id, mode="rw", token=self.token)
    users = fd.Schema.USER()
    users.Append(rdfvalue.User(
        username="LocalService", domain="testing-PC",
        homedir=r"C:\Users\localservice", sid="S-1-5-20"))
    fd.Set(users)
    fd.Close()

    # Get KB initialized
    for _ in test_lib.TestFlowHelper(
        "KnowledgeBaseInitializationFlow", client_mock,
        client_id=self.client_id, token=self.token):
      pass

    artifact_list = ["WindowsPersistenceMechanismFiles"]
    with test_lib.Instrument(
        transfer.MultiGetFile, "Start") as getfile_instrument:
      for _ in test_lib.TestFlowHelper("ArtifactCollectorFlow", client_mock,
                                       artifact_list=artifact_list,
                                       token=self.token,
                                       client_id=self.client_id,
                                       output="analysis/{p}/{u}-{t}",
                                       split_output_by_artifact=True):
        pass

      # Check MultiGetFile got called for our runkey files
      paths = [u"C:\\Program Files\\Windows Sidebar\\Sidebar.exe",
               u"C:\\Windows\\TEMP\\Sidebar.exe"]
      for pathspec in getfile_instrument.args[0][0].args.pathspecs:
        self.assertTrue(pathspec.path in paths)
      self.assertEqual(len(getfile_instrument.args[0][0].args.pathspecs), 2)

    artifact_list = ["BadPathspecArtifact"]
    with test_lib.Instrument(
        transfer.MultiGetFile, "Start") as getfile_instrument:
      for _ in test_lib.TestFlowHelper("ArtifactCollectorFlow", client_mock,
                                       artifact_list=artifact_list,
                                       token=self.token,
                                       client_id=self.client_id,
                                       output="analysis/{p}/{u}-{t}",
                                       split_output_by_artifact=True):
        pass

      self.assertFalse(getfile_instrument.args)


