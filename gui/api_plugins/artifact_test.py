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

  def _renderEmptyArtifacts(self):
    artifact_registry.REGISTRY.ClearSources()
    return self.handler.Render(self.handler.args_type(), token=self.token)

  def testNoArtifacts(self):
    rendering = self._renderEmptyArtifacts()
    self.assertEqual(rendering,
                     {"count": 0, "items": [], "offset": 0, "total_count": 0})

  def _renderTestArtifacts(self):
    return self.handler.Render(self.handler.args_type(), token=self.token)

  def testPrepackagedArtifacts(self):
    rendering = self._renderTestArtifacts()

    # we know there are some prepackaged artifacts
    self.assertTrue(rendering)

    # test for a prepackaged artifact we know to exist
    for item in rendering["items"]:
      if item["value"]["artifact"]["value"]["name"]["value"] == "FakeArtifact":
        fake_artifact = item["value"]

    self.assertTrue(fake_artifact)
    self.assertIn("is_custom", fake_artifact)
    self.assertFalse(fake_artifact["is_custom"]["value"])

    for required_key in ("doc",
                         "labels",
                         "supported_os"):
      self.assertIn(required_key, fake_artifact["artifact"]["value"])


class ArtifactHandlerRegressionTest(
    api_test_lib.ApiCallHandlerRegressionTest):

  handler = "ApiArtifactHandler"

  def Run(self):
    artifact_registry.REGISTRY.ClearSources()
    test_artifacts_file = os.path.join(
        config_lib.CONFIG["Test.data_dir"], "artifacts", "test_artifact.json")
    artifact_registry.REGISTRY.AddFileSource(test_artifacts_file)

    self.Check("GET", "/api/artifacts")


class ApiDeleteArtifactsHandlerTest(test_lib.GRRBaseTest):

  def setUp(self):
    super(ApiDeleteArtifactsHandlerTest, self).setUp()
    self.handler = artifact_plugin.ApiDeleteArtifactsHandler()

  def UploadTestArtifacts(self):
    artifact_registry.REGISTRY.ClearRegistry()
    test_artifacts_file = os.path.join(
        config_lib.CONFIG["Test.data_dir"], "artifacts", "test_artifacts.json")
    with open(test_artifacts_file) as fd:
      artifact.UploadArtifactYamlFile(fd.read(), token=self.token)

  def testDeletesArtifactsWithSpecifiedNames(self):
    self.UploadTestArtifacts()
    count = len(artifact_registry.REGISTRY.GetArtifacts(
        reload_datastore_artifacts=True))

    args = self.handler.args_type(names=["TestFilesArtifact",
                                         "WMIActiveScriptEventConsumer"])
    response = self.handler.Render(args, token=self.token)
    self.assertEqual(response, dict(status="OK"))

    new_count = len(artifact_registry.REGISTRY.GetArtifacts())

    # Check that we deleted exactly 2 artifacts.
    self.assertEqual(new_count, count - 2)

  def testDeleteDependency(self):
    self.UploadTestArtifacts()
    args = self.handler.args_type(names=["TestAggregationArtifact"])
    with self.assertRaises(ValueError):
      self.handler.Render(args, token=self.token)

  def testDeleteNonExistentArtifact(self):
    self.UploadTestArtifacts()
    args = self.handler.args_type(names=["NonExistentArtifact"])
    e = self.assertRaises(ValueError)
    with e:
      self.handler.Render(args, token=self.token)
    self.assertEqual(str(e.exception),
                     "Artifact(s) to delete (NonExistentArtifact) not found.")


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
