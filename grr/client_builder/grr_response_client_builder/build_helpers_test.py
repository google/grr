#!/usr/bin/env python
"""Tests for building and repacking clients."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import io
import os
from unittest import mock

from absl import app

from grr_response_client_builder import build_helpers
from grr_response_core import config
from grr_response_core.lib import config_lib
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.util.compat import yaml
from grr.test_lib import test_lib


class BuildTests(test_lib.GRRBaseTest):
  """Tests for building functionality."""

  def testWriteBuildYaml(self):
    """Test build.yaml is output correctly."""
    context = [
        "Target:LinuxDeb", "Platform:Linux", "Target:Linux", "Arch:amd64"
    ]
    expected = {
        "Client.build_environment":
            "cp27-cp27mu-linux_x86_64",
        "Client.build_time":
            "2016-05-24 20:04:25",
        "Template.build_type":
            "Release",
        "Template.build_context":
            context,
        "Template.version_major":
            str(config.CONFIG.Get("Source.version_major")),
        "Template.version_minor":
            str(config.CONFIG.Get("Source.version_minor")),
        "Template.version_revision":
            str(config.CONFIG.Get("Source.version_revision")),
        "Template.version_release":
            str(config.CONFIG.Get("Source.version_release")),
        "Template.arch":
            u"amd64"
    }

    fd = io.StringIO()

    with mock.patch.object(rdf_client.Uname, "FromCurrentSystem") as fcs:
      fcs.return_value.signature.return_value = "cp27-cp27mu-linux_x86_64"
      with test_lib.FakeTime(1464120265):
        build_helpers.WriteBuildYaml(fd, context=context)

    self.assertEqual(yaml.Parse(fd.getvalue()), expected)

  def testGenClientConfig(self):
    with test_lib.ConfigOverrider({"Client.build_environment": "test_env"}):

      data = build_helpers.GetClientConfig(["Client Context"], validate=True)

      parser = config_lib.YamlParser(data=data)
      raw_data = parser.RawData()

      self.assertIn("Client.deploy_time", raw_data)

  def testGenClientConfig_ignoreBuilderContext(self):
    with test_lib.PreserveConfig():
      # Define a secondary config with special values for the ClientBuilder
      # context.
      str_override = """
        Test Context:
          Client.labels: [label0, label1]
          ClientBuilder Context:
            Client.labels: [build-label0, build-label1]
      """
      override = config_lib.YamlParser(data=str_override).RawData()
      config.CONFIG.MergeData(override)
      # Sanity-check that the secondary config was merged into the global
      # config.
      self.assertEqual(config.CONFIG["Client.labels"], ["label0", "label1"])

      context = ["Test Context", "ClientBuilder Context", "Client Context"]
      str_client_config = build_helpers.GetClientConfig(context)
      client_config = config_lib.YamlParser(data=str_client_config).RawData()
      # Settings particular to the ClientBuilder context should not carry over
      # into the generated client config.
      self.assertEqual(client_config["Client.labels"], ["label0", "label1"])

  def testRepackerDummyClientConfig(self):
    """Ensure our dummy client config can pass validation.

    This config is used to exercise repacking code in integration testing, here
    we just make sure it will pass validation.
    """
    new_config = config.CONFIG.MakeNewConfig()
    new_config.Initialize()
    new_config.LoadSecondaryConfig(
        os.path.join(config.CONFIG["Test.data_dir"], "dummyconfig.yaml"))
    context = ["Test Context", "ClientBuilder Context", "Client Context"]
    build_helpers.ValidateEndConfig(new_config, context=context)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
