#!/usr/bin/env python
"""This modules contains regression tests for artifact API handler."""



import os


from grr import config
from grr.gui import api_regression_test_lib
from grr.gui.api_plugins import artifact as artifact_plugin
from grr.lib import flags
from grr.server import artifact_registry


class ApiListArtifacstHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest):

  api_method = "ListArtifacts"
  handler = artifact_plugin.ApiListArtifactsHandler

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
