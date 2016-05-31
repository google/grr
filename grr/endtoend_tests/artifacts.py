#!/usr/bin/env python
"""End to end tests that run ArtifactCollectorFlow."""


from grr.endtoend_tests import base
from grr.lib import aff4
from grr.lib.aff4_objects import collects
from grr.lib.rdfvalues import client as rdf_client


class TestDarwinPersistenceMechanisms(base.AutomatedTest):
  """Test DarwinPersistenceMechanisms."""
  platforms = ["Darwin"]
  flow = "ArtifactCollectorFlow"
  test_output_path = "analysis/persistence/testing"
  args = {"artifact_list": ["DarwinPersistenceMechanisms"],
          "output": test_output_path}

  def CheckFlow(self):
    output_urn = self.client_id.Add(self.test_output_path)
    collection = aff4.FACTORY.Open(output_urn, mode="r", token=self.token)
    self.assertIsInstance(collection, collects.RDFValueCollection)
    persistence_list = list(collection)
    # Make sure there are at least some results.
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
  test_output_path = "analysis/diskusage/testing"
  args = {"artifact_list": ["RootDiskVolumeUsage"],
          "output": test_output_path}

  def CheckFlow(self):
    output_urn = self.client_id.Add(self.test_output_path)
    collection = aff4.FACTORY.Open(output_urn, mode="r", token=self.token)
    self.assertIsInstance(collection, collects.RDFValueCollection)
    volume_list = list(collection)
    # Make sure there are at least some results.
    self.assertEqual(len(volume_list), 1)
    self.assertEqual(volume_list[0].unixvolume.mount_point, "/")
    self.assertTrue(isinstance(volume_list[0].FreeSpacePercent(), float))


class TestParserDependency(base.AutomatedTest):
  """Test Artifacts complete when KB is empty."""
  platforms = ["Windows"]
  flow = "ArtifactCollectorFlow"
  test_output_path = "analysis/testing/TestParserDependency"
  args = {"artifact_list": ["WinPathEnvironmentVariable"], "dependencies":
          "FETCH_NOW", "output": test_output_path}

  def setUp(self):
    # Set the KB to an empty object
    client = aff4.FACTORY.Open(self.client_id, mode="rw", token=self.token)
    self.old_kb = client.Get(client.Schema.KNOWLEDGE_BASE)
    client.Set(client.Schema.KNOWLEDGE_BASE, rdf_client.KnowledgeBase())
    client.Flush()
    super(TestParserDependency, self).setUp()

  def CheckFlow(self):
    output_urn = self.client_id.Add(self.test_output_path)
    self.collection = aff4.FACTORY.Open(output_urn, mode="r", token=self.token)
    self.assertIsInstance(self.collection, collects.RDFValueCollection)
    volume_list = list(self.collection)
    # Make sure there are at least some results.
    self.assertTrue(volume_list)

  def tearDown(self):
    # Set the KB to an empty object
    client = aff4.FACTORY.Open(self.client_id, mode="rw", token=self.token)
    client.Set(client.Schema.KNOWLEDGE_BASE, self.old_kb)
    client.Flush()
    super(TestParserDependency, self).tearDown()


class TestParserDependencyWinDir(TestParserDependency):
  test_output_path = "analysis/testing/TestParserDependencyWinDir"
  args = {"artifact_list": ["WinDirEnvironmentVariable"], "dependencies":
          "FETCH_NOW", "output": test_output_path}


class TestParserDependencyTemp(TestParserDependency):
  test_output_path = "analysis/testing/TestParserDependencyTemp"
  args = {"artifact_list": ["TempEnvironmentVariable"], "dependencies":
          "FETCH_NOW", "output": test_output_path}


class TestParserDependencyUserShellFolders(TestParserDependency):
  test_output_path = "analysis/testing/TestParserDependencyUserShellFolders"
  args = {"artifact_list": ["UserShellFolders"],
          "dependencies": "FETCH_NOW",
          "output": test_output_path}

  def CheckFlow(self):
    super(TestParserDependencyUserShellFolders, self).CheckFlow()
    for userobj in self.collection:
      self.assertTrue(userobj.appdata)
      self.assertTrue(userobj.temp)
