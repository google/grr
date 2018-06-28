#!/usr/bin/env python
"""Tests the client artifactor collection."""
import os

from grr import config
from grr.lib import flags
from grr.test_lib import artifact_test_lib
from grr.test_lib import client_test_lib
from grr.test_lib import test_lib


class ArtifactCollectorTest(client_test_lib.EmptyActionTest):

  def setUp(self):
    super(ArtifactCollectorTest, self).setUp()
    self.test_artifacts_file = os.path.join(config.CONFIG["Test.data_dir"],
                                            "artifacts", "test_artifacts.json")

  @artifact_test_lib.PatchCleanArtifactRegistry
  def testRegistry(self, registry):
    """Test artifact registry can be used on client for testing."""
    registry.AddFileSource(self.test_artifacts_file)
    art_obj = registry.GetArtifact("TestCmdArtifact")
    self.assertEqual(art_obj.name, "TestCmdArtifact")


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
