#!/usr/bin/env python
"""This modules contains tests for artifact API handler."""


import copy
import os

from grr import config
from grr.gui import api_test_lib
from grr.gui.api_plugins import artifact as artifact_plugin
from grr.lib import flags
from grr.server import artifact
from grr.server import artifact_registry
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib


class ArtifactRegistryCleanupMixin(object):
  """Mixin used to cleanup changes made to the global artifact registry."""

  # TODO(hanuszczak): Using mixins like this is dirty. Find a better way to
  # handle registry changes. Refer to `ArtifactHandlingTest` comment in [1] for
  # similar hacks.
  #
  # [1]: grr/server/artifact_utils_test.py

  def setUp(self):
    super(ArtifactRegistryCleanupMixin, self).setUp()

    registry = artifact_registry.REGISTRY
    self._original_registry_sources = copy.deepcopy(registry._sources)
    self._original_registry_artifacts = copy.deepcopy(registry._artifacts)

  def tearDown(self):
    super(ArtifactRegistryCleanupMixin, self).tearDown()

    registry = artifact_registry.REGISTRY
    registry._artifacts = self._original_registry_artifacts
    registry._sources = self._original_registry_sources
    registry._dirty = True


class ApiListArtifactsHandlerTest(ArtifactRegistryCleanupMixin,
                                  flow_test_lib.FlowTestsBaseclass):
  """Test for ApiListArtifactsHandler."""

  def setUp(self):
    super(ApiListArtifactsHandlerTest, self).setUp()
    self.handler = artifact_plugin.ApiListArtifactsHandler()
    test_artifacts_file = os.path.join(config.CONFIG["Test.data_dir"],
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


class ApiUploadArtifactHandlerTest(ArtifactRegistryCleanupMixin,
                                   api_test_lib.ApiCallHandlerTest):

  def setUp(self):
    super(ApiUploadArtifactHandlerTest, self).setUp()
    self.handler = artifact_plugin.ApiUploadArtifactHandler()

  def testUpload(self):
    artifact_registry.REGISTRY.ClearRegistry()

    test_artifacts_file = os.path.join(config.CONFIG["Test.data_dir"],
                                       "artifacts", "test_artifact.json")
    with open(test_artifacts_file, "rb") as fd:
      args = self.handler.args_type(artifact=fd.read())

    with self.assertRaises(artifact_registry.ArtifactNotRegisteredError):
      artifact_registry.REGISTRY.GetArtifact("TestDrivers")

    self.handler.Handle(args, token=self.token)

    artifact_registry.REGISTRY.GetArtifact("TestDrivers")


class ApiDeleteArtifactsHandlerTest(ArtifactRegistryCleanupMixin,
                                    api_test_lib.ApiCallHandlerTest):

  def setUp(self):
    super(ApiDeleteArtifactsHandlerTest, self).setUp()
    self.handler = artifact_plugin.ApiDeleteArtifactsHandler()

  def UploadTestArtifacts(self):
    artifact_registry.REGISTRY.ClearRegistry()
    test_artifacts_file = os.path.join(config.CONFIG["Test.data_dir"],
                                       "artifacts", "test_artifacts.json")
    with open(test_artifacts_file, "rb") as fd:
      artifact.UploadArtifactYamlFile(fd.read())

  def testDeletesArtifactsWithSpecifiedNames(self):
    self.UploadTestArtifacts()
    count = len(
        artifact_registry.REGISTRY.GetArtifacts(
            reload_datastore_artifacts=True))

    args = self.handler.args_type(
        names=["TestFilesArtifact", "WMIActiveScriptEventConsumer"])
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
