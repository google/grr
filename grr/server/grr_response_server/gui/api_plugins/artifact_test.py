#!/usr/bin/env python
"""This modules contains tests for artifact API handler."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import os

from grr_response_core import config
from grr_response_core.lib import flags
from grr_response_core.lib.rdfvalues import artifacts as rdf_artifacts
from grr_response_server import artifact
from grr_response_server.gui import api_test_lib
from grr_response_server.gui.api_plugins import artifact as artifact_plugin
from grr.test_lib import artifact_test_lib
from grr.test_lib import db_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib


@db_test_lib.DualDBTest
class ApiListArtifactsHandlerTest(flow_test_lib.FlowTestsBaseclass):
  """Test for ApiListArtifactsHandler."""

  def setUp(self):
    super(ApiListArtifactsHandlerTest, self).setUp()
    self.handler = artifact_plugin.ApiListArtifactsHandler()

  @artifact_test_lib.PatchCleanArtifactRegistry
  def testNoArtifacts(self, _):
    result = self.handler.Handle(self.handler.args_type(), token=self.token)

    self.assertEqual(result.total_count, 0)
    self.assertEqual(result.items, [])

  @artifact_test_lib.PatchDefaultArtifactRegistry
  def testPrepackagedArtifacts(self, registry):
    test_artifacts_file = os.path.join(config.CONFIG["Test.data_dir"],
                                       "artifacts", "test_artifacts.json")
    registry.AddFileSource(test_artifacts_file)

    result = self.handler.Handle(self.handler.args_type(), token=self.token)

    # Some artifacts are guaranteed to be returned, as they're defined in
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


@db_test_lib.DualDBTest
class ApiUploadArtifactHandlerTest(api_test_lib.ApiCallHandlerTest):

  def setUp(self):
    super(ApiUploadArtifactHandlerTest, self).setUp()
    self.handler = artifact_plugin.ApiUploadArtifactHandler()

  @artifact_test_lib.PatchCleanArtifactRegistry
  def testUpload(self, registry):
    test_artifacts_file = os.path.join(config.CONFIG["Test.data_dir"],
                                       "artifacts", "test_artifact.json")
    with open(test_artifacts_file, "rb") as fd:
      args = self.handler.args_type(artifact=fd.read())

    with self.assertRaises(rdf_artifacts.ArtifactNotRegisteredError):
      registry.GetArtifact("TestDrivers")

    self.handler.Handle(args, token=self.token)

    registry.GetArtifact("TestDrivers")


@db_test_lib.DualDBTest
@artifact_test_lib.PatchDefaultArtifactRegistry
class ApiDeleteArtifactsHandlerTest(api_test_lib.ApiCallHandlerTest):

  def setUp(self):
    super(ApiDeleteArtifactsHandlerTest, self).setUp()
    self.handler = artifact_plugin.ApiDeleteArtifactsHandler()

  def UploadTestArtifacts(self):
    test_artifacts_file = os.path.join(config.CONFIG["Test.data_dir"],
                                       "artifacts", "test_artifacts.json")
    with open(test_artifacts_file, "rb") as fd:
      artifact.UploadArtifactYamlFile(fd.read())

  def testDeletesArtifactsWithSpecifiedNames(self, registry):
    self.UploadTestArtifacts()
    count = len(registry.GetArtifacts(reload_datastore_artifacts=True))

    args = self.handler.args_type(
        names=["TestFilesArtifact", "WMIActiveScriptEventConsumer"])
    self.handler.Handle(args, token=self.token)

    new_count = len(registry.GetArtifacts())

    # Check that we deleted exactly 2 artifacts.
    self.assertEqual(new_count, count - 2)

  def testDeleteDependency(self, registry):
    self.UploadTestArtifacts()
    args = self.handler.args_type(names=["TestAggregationArtifact"])
    with self.assertRaises(ValueError):
      self.handler.Handle(args, token=self.token)

  def testDeleteNonExistentArtifact(self, registry):
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
