#!/usr/bin/env python
"""This modules contains tests for artifact API handler."""



import os

from grr.gui import api_test_lib
from grr.gui.api_plugins import artifact as artifact_plugin
from grr.lib import artifact
from grr.lib import artifact_registry
from grr.lib import config_lib
from grr.lib import flags
from grr.lib import test_lib


class ApiListArtifactsHandlerTest(test_lib.FlowTestsBaseclass):
  """Test for ApiListArtifactsHandler."""

  def setUp(self):
    super(ApiListArtifactsHandlerTest, self).setUp()
    self.handler = artifact_plugin.ApiListArtifactsHandler()
    test_artifacts_file = os.path.join(config_lib.CONFIG["Test.data_dir"],
                                       "artifacts", "test_artifacts.json")
    artifact_registry.REGISTRY.AddFileSource(test_artifacts_file)

  def _handleEmptyArtifacts(self):
    artifact_registry.REGISTRY.ClearSources()
    return self.handler.Handle(self.handler.args_type(), token=self.token)

  def testNoArtifacts(self):
    result = self._handleEmptyArtifacts()
    self.assertEqual(result.total_count, 0)
    self.assertEqual(result.items, [])

  def _handleTestArtifacts(self):
    return self.handler.Handle(self.handler.args_type(), token=self.token)

  def testPrepackagedArtifacts(self):
    result = self._handleTestArtifacts()

    # Some artifacts are guaratneed to be returned, as they're defined in
    # the test_data/artifacts/test_artifacts.json.
    self.assertTrue(result.total_count)

    # Check that FakeArtifact artifact exists. It's guaranteed to exist, since
    # it's defined in test_data/artifacts/test_artifacts.json.
    for item in result.items:
      if item.artifact.name == "FakeArtifact":
        fake_artifact = item

    self.assertTrue(fake_artifact)
    self.assertTrue(fake_artifact.HasField("is_custom"))
    self.assertFalse(fake_artifact.is_custom)

    self.assertTrue(fake_artifact.artifact.doc)
    self.assertTrue(fake_artifact.artifact.labels)
    self.assertTrue(fake_artifact.artifact.supported_os)


class ArtifactHandlerRegressionTest(api_test_lib.ApiCallHandlerRegressionTest):

  handler = "ApiArtifactHandler"

  def Run(self):
    artifact_registry.REGISTRY.ClearSources()
    test_artifacts_file = os.path.join(config_lib.CONFIG["Test.data_dir"],
                                       "artifacts", "test_artifact.json")
    artifact_registry.REGISTRY.AddFileSource(test_artifacts_file)

    self.Check("GET", "/api/artifacts")


class ApiDeleteArtifactsHandlerTest(test_lib.GRRBaseTest):

  def setUp(self):
    super(ApiDeleteArtifactsHandlerTest, self).setUp()
    self.handler = artifact_plugin.ApiDeleteArtifactsHandler()

  def UploadTestArtifacts(self):
    artifact_registry.REGISTRY.ClearRegistry()
    test_artifacts_file = os.path.join(config_lib.CONFIG["Test.data_dir"],
                                       "artifacts", "test_artifacts.json")
    with open(test_artifacts_file) as fd:
      artifact.UploadArtifactYamlFile(fd.read(), token=self.token)

  def testDeletesArtifactsWithSpecifiedNames(self):
    self.UploadTestArtifacts()
    count = len(artifact_registry.REGISTRY.GetArtifacts(
        reload_datastore_artifacts=True))

    args = self.handler.args_type(names=["TestFilesArtifact",
                                         "WMIActiveScriptEventConsumer"])
    self.handler.Handle(args, token=self.token)

    new_count = len(artifact_registry.REGISTRY.GetArtifacts())

    # Check that we deleted exactly 2 artifacts.
    self.assertEqual(new_count, count - 2)

  def testDeleteDependency(self):
    self.UploadTestArtifacts()
    args = self.handler.args_type(names=["TestAggregationArtifact"])
    with self.assertRaises(ValueError):
      self.handler.Handle(args, token=self.token)

  def testDeleteNonExistentArtifact(self):
    self.UploadTestArtifacts()
    args = self.handler.args_type(names=["NonExistentArtifact"])
    e = self.assertRaises(ValueError)
    with e:
      self.handler.Handle(args, token=self.token)
    self.assertEqual(
        str(e.exception),
        "Artifact(s) to delete (NonExistentArtifact) not found.")


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
