#!/usr/bin/env python
"""End to end tests that run ArtifactCollectorFlow."""


from grr.endtoend_tests import base
from grr.lib import aff4
from grr.lib import flow_runner
from grr.lib.rdfvalues import client as rdf_client


class TestDarwinPersistenceMechanisms(base.AutomatedTest):
  """Test DarwinPersistenceMechanisms."""
  platforms = ["Darwin"]
  flow = "ArtifactCollectorFlow"
  args = {"artifact_list": ["DarwinPersistenceMechanisms"]}

  def CheckFlow(self):
    persistence_list = self.CheckCollectionNotEmptyWithRetry(
        self.session_id.Add(flow_runner.RESULTS_SUFFIX), self.token)
    self.assertGreater(len(persistence_list), 5)
    launchservices = "/System/Library/CoreServices/launchservicesd"

    for p in persistence_list:
      if p.pathspec.path == launchservices:
        return
    self.fail("Service listing does not contain launchservices: %s." %
              launchservices)


class TestRootDiskVolumeUsage(base.AutomatedTest):
  """Test RootDiskVolumeUsage."""
  platforms = ["Linux", "Darwin"]
  flow = "ArtifactCollectorFlow"
  args = {"artifact_list": ["RootDiskVolumeUsage"]}

  def CheckFlow(self):
    volume_list = self.CheckCollectionNotEmptyWithRetry(
        self.session_id.Add(flow_runner.RESULTS_SUFFIX), self.token)
    self.assertEqual(volume_list[0].unixvolume.mount_point, "/")
    self.assertTrue(isinstance(volume_list[0].FreeSpacePercent(), float))


class TestParserDependency(base.AutomatedTest):
  """Test Artifacts complete when KB is empty."""
  platforms = ["Windows"]
  flow = "ArtifactCollectorFlow"
  args = {"artifact_list": ["WinPathEnvironmentVariable"], "dependencies":
          "FETCH_NOW"}

  def setUp(self):
    # Set the KB to an empty object
    client = aff4.FACTORY.Open(self.client_id, mode="rw", token=self.token)
    self.old_kb = client.Get(client.Schema.KNOWLEDGE_BASE)
    client.Set(client.Schema.KNOWLEDGE_BASE, rdf_client.KnowledgeBase())
    client.Flush()
    super(TestParserDependency, self).setUp()

  def CheckFlow(self):
    self.collection = self.CheckCollectionNotEmptyWithRetry(
        self.session_id.Add(flow_runner.RESULTS_SUFFIX), self.token)

  def tearDown(self):
    client = aff4.FACTORY.Open(self.client_id, mode="rw", token=self.token)
    client.Set(client.Schema.KNOWLEDGE_BASE, self.old_kb)
    client.Flush()
    super(TestParserDependency, self).tearDown()


class TestParserDependencyWinDir(TestParserDependency):
  args = {"artifact_list": ["WinDirEnvironmentVariable"], "dependencies":
          "FETCH_NOW"}


class TestParserDependencyTemp(TestParserDependency):
  args = {"artifact_list": ["TempEnvironmentVariable"], "dependencies":
          "FETCH_NOW"}


class TestParserDependencyUserShellFolders(TestParserDependency):
  args = {"artifact_list": ["UserShellFolders"], "dependencies": "FETCH_NOW"}

  def CheckFlow(self):
    super(TestParserDependencyUserShellFolders, self).CheckFlow()
    for userobj in self.collection:
      self.assertTrue(userobj.appdata)
      self.assertTrue(userobj.temp)
