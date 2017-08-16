#!/usr/bin/env python
"""End to end tests that run ArtifactCollectorFlow."""


from grr.endtoend_tests import base
from grr.lib.rdfvalues import client as rdf_client
from grr.server import aff4
from grr.server.aff4_objects import aff4_grr
from grr.server.flows.general import collectors


class TestDarwinPersistenceMechanisms(base.AutomatedTest):
  """Test DarwinPersistenceMechanisms."""
  platforms = ["Darwin"]
  flow = collectors.ArtifactCollectorFlow.__name__
  args = {"artifact_list": ["DarwinPersistenceMechanisms"]}

  def CheckFlow(self):
    persistence_list = self.CheckResultCollectionNotEmptyWithRetry(
        self.session_id)
    self.assertGreater(len(persistence_list), 5)
    launchservices = "/System/Library/CoreServices/launchservicesd"

    for p in persistence_list:
      if p.pathspec.path == launchservices:
        return
    self.fail(
        "Service listing does not contain launchservices: %s." % launchservices)


class TestRootDiskVolumeUsage(base.AutomatedTest):
  """Test RootDiskVolumeUsage."""
  platforms = ["Linux", "Darwin"]
  flow = collectors.ArtifactCollectorFlow.__name__
  args = {"artifact_list": ["RootDiskVolumeUsage"]}

  def CheckFlow(self):
    volume_list = self.CheckResultCollectionNotEmptyWithRetry(self.session_id)
    self.assertEqual(volume_list[0].unixvolume.mount_point, "/")
    self.assertTrue(isinstance(volume_list[0].FreeSpacePercent(), float))


class TestParserDependency(base.AutomatedTest):
  """Test Artifacts complete when KB is empty."""
  platforms = ["Windows"]
  flow = collectors.ArtifactCollectorFlow.__name__
  args = {
      "artifact_list": ["WindowsEnvironmentVariablePath"],
      "dependencies": "FETCH_NOW"
  }

  def setUp(self):
    # We need to store the KB so we can put it back after the test.
    client = aff4.FACTORY.Open(self.client_id, mode="rw", token=self.token)
    kb_backup = aff4.FACTORY.Create(
        self.client_id.Add("temp").Add("TestParserDependency"),
        aff4_grr.TempKnowledgeBase,
        token=self.token)
    kb_backup.Set(kb_backup.Schema.KNOWLEDGE_BASE,
                  client.Get(client.Schema.KNOWLEDGE_BASE))
    kb_backup.Close()

    # Set the KB to an empty object
    client.Set(client.Schema.KNOWLEDGE_BASE, rdf_client.KnowledgeBase())
    client.Flush()
    super(TestParserDependency, self).setUp()

  def CheckFlow(self):
    self.collection = self.CheckResultCollectionNotEmptyWithRetry(
        self.session_id)

  def tearDown(self):
    client = aff4.FACTORY.Open(self.client_id, mode="rw", token=self.token)
    old_kb = aff4.FACTORY.Open(
        self.client_id.Add("temp").Add("TestParserDependency"),
        token=self.token)
    client.Set(client.Schema.KNOWLEDGE_BASE,
               old_kb.Get(old_kb.Schema.KNOWLEDGE_BASE))
    client.Flush()
    aff4.FACTORY.Delete(
        self.client_id.Add("temp").Add("TestParserDependency"),
        token=self.token)
    super(TestParserDependency, self).tearDown()


class TestParserDependencyWinDir(TestParserDependency):
  args = {
      "artifact_list": ["WindowsEnvironmentVariableWinDir"],
      "dependencies": "FETCH_NOW"
  }


class TestParserDependencyTemp(TestParserDependency):
  args = {
      "artifact_list": ["WindowsEnvironmentVariableTemp"],
      "dependencies": "FETCH_NOW"
  }


class TestParserDependencyUserShellFolders(TestParserDependency):
  args = {
      "artifact_list": ["WindowsUserShellFolders"],
      "dependencies": "FETCH_NOW"
  }

  def CheckFlow(self):
    super(TestParserDependencyUserShellFolders, self).CheckFlow()
    for userobj in self.collection:
      self.assertTrue(userobj.appdata)
      self.assertTrue(userobj.temp)
