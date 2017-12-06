#!/usr/bin/env python
"""This modules contains regression tests for artifact API handler."""


import copy
import os


from grr import config
from grr.gui import api_regression_test_lib
from grr.gui.api_plugins import artifact as artifact_plugin
from grr.lib import flags
from grr.server import artifact_registry


class ApiListArtifactsHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest):

  api_method = "ListArtifacts"
  handler = artifact_plugin.ApiListArtifactsHandler

  # TODO(hanuszczak): This is again a hack to cleanup changes made to the
  # artifact registry. Similar things are done in [1] and [2]. This should be
  # refactored in some nicer way in the future.
  #
  # [1]: grr/server/artifact_utils_test.py
  # [2]: grr/gui/api_plugins/artifact_test.py

  def setUp(self):
    super(ApiListArtifactsHandlerRegressionTest, self).setUp()

    registry = artifact_registry.REGISTRY
    self.original_registry_sources = copy.deepcopy(registry._sources)

  def tearDown(self):
    super(ApiListArtifactsHandlerRegressionTest, self).tearDown()

    registry = artifact_registry.REGISTRY
    registry._sources = self.original_registry_sources
    registry._dirty = True

  def Run(self):
    artifact_registry.REGISTRY.ClearSources()
    test_artifacts_file = os.path.join(config.CONFIG["Test.data_dir"],
                                       "artifacts", "test_artifact.json")
    artifact_registry.REGISTRY.AddFileSource(test_artifacts_file)

    self.Check("ListArtifacts")


def main(argv):
  api_regression_test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
