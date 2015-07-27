#!/usr/bin/env python
"""This modules contains tests for artifact API renderer."""



import os

from grr.gui import api_test_lib
from grr.gui.api_plugins import artifact as artifact_plugin
from grr.lib import artifact_registry
from grr.lib import artifact_test
from grr.lib import config_lib
from grr.lib import flags
from grr.lib import test_lib


class ArtifactRendererTest(artifact_test.ArtifactBaseTest):
  """Test for ArtifactRendererTest."""

  def setUp(self):
    super(ArtifactRendererTest, self).setUp()
    self.renderer = artifact_plugin.ApiArtifactRenderer()
    self.LoadTestArtifacts()

  def _renderEmptyArtifacts(self):
    artifact_registry.REGISTRY.ClearSources()
    return self.renderer.Render(None, token=self.token)

  def testNoArtifacts(self):
    rendering = self._renderEmptyArtifacts()
    self.assertEqual(rendering, {})
    self.assertFalse(rendering)

  def _renderTestArtifacts(self):
    return self.renderer.Render(None, token=self.token)

  def testPrepackagedArtifacts(self):
    rendering = self._renderTestArtifacts()

    # we know there are some prepackaged artifacts
    self.assertTrue(rendering)

    # test for a prepackaged artifact we know to exist
    self.assertIn("FakeArtifact", rendering)
    self.assertIn("custom", rendering["FakeArtifact"])
    self.assertIn("processors", rendering["FakeArtifact"])
    self.assertFalse(rendering["FakeArtifact"]["custom"])

    for required_key in ("doc",
                         "labels",
                         "supported_os"):
      self.assertIn(required_key, rendering["FakeArtifact"]["artifact"])


class ArtifactRendererRegressionTest(
    api_test_lib.ApiCallRendererRegressionTest):

  renderer = "ApiArtifactRenderer"

  def Run(self):
    artifact_registry.REGISTRY.ClearSources()
    test_artifacts_file = os.path.join(
        config_lib.CONFIG["Test.data_dir"], "artifacts", "test_artifact.json")
    artifact_registry.REGISTRY.AddFileSource(test_artifacts_file)

    self.Check("GET", "/api/artifacts")


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
