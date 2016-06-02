#!/usr/bin/env python
"""Tests for building and repacking clients."""
import StringIO
import mock
import yaml

from grr.lib import build
from grr.lib import config_lib
from grr.lib import flags
from grr.lib import test_lib
from grr.lib.rdfvalues import client as rdf_client


class BuildTests(test_lib.GRRBaseTest):
  """Tests for building functionality."""

  def testWriteBuildYaml(self):
    """Test build.yaml is output correctly."""
    context = ["Target:LinuxDeb", "Platform:Linux", "Target:Linux",
               "Arch:amd64"]
    expected = {"Client.build_environment": "cp27-cp27mu-linux_x86_64",
                "Client.build_time": "2016-05-24 20:04:25",
                "Template.build_type": "Release",
                "Template.build_context": ["ClientBuilder Context"] + context,
                "Template.version_major":
                    str(config_lib.CONFIG.Get("Source.version_major")),
                "Template.version_minor":
                    str(config_lib.CONFIG.Get("Source.version_minor")),
                "Template.version_revision":
                    str(config_lib.CONFIG.Get("Source.version_revision")),
                "Template.version_release":
                    str(config_lib.CONFIG.Get("Source.version_release")),
                "Template.arch": u"amd64"}

    fd = StringIO.StringIO()
    builder = build.ClientBuilder(context=context)

    with mock.patch.object(rdf_client.Uname, "FromCurrentSystem") as fcs:
      fcs.return_value.signature.return_value = "cp27-cp27mu-linux_x86_64"
      with test_lib.FakeTime(1464120265):
        builder.WriteBuildYaml(fd)

    fd.seek(0)
    self.assertEqual(dict(yaml.load(fd)), expected)

  def testGenClientConfig(self):
    with test_lib.ConfigOverrider({"Client.build_environment": "test_env"}):

      deployer = build.ClientRepacker()
      data = deployer.GetClientConfig(["Client Context"], validate=True)

      parser = config_lib.YamlParser(data=data)
      raw_data = parser.RawData()

      self.assertIn("Client.deploy_time", raw_data)


def main(argv):
  test_lib.GrrTestProgram(argv=argv)


if __name__ == "__main__":
  flags.StartMain(main)
