#!/usr/bin/env python
"""Tests for grr.lib.rdfvalues.artifacts."""

from grr.lib import parsers
from grr.lib import rdfvalue
from grr.lib import utils
from grr.lib.rdfvalues import test_base


class ArtifactTests(test_base.RDFValueTestCase):
  """Test the Artifact implementation."""

  rdfvalue_class = rdfvalue.Artifact

  def GenerateSample(self, number=0):
    result = rdfvalue.Artifact(name="artifact%s" % number,
                               doc="Doco",
                               provides="environ_windir",
                               supported_os="Windows",
                               urls="http://blah")
    return result

  def testGetArtifactPathDependencies(self):
    # pylint: disable=g-line-too-long
    collectors = [
        {"collector_type": rdfvalue.Collector.CollectorType.REGISTRY_VALUE, "args": {
            "path": r"%%current_control_set%%\Control\Session Manager\Environment\Path"}},
        {"collector_type": rdfvalue.Collector.CollectorType.WMI, "args": {
            "query": "SELECT * FROM Win32_UserProfile WHERE SID='%%users.sid%%'"}},
        {"collector_type": rdfvalue.Collector.CollectorType.GREP, "args": {"content_regex_list": ["^%%users.username%%:"]}}]
    # pylint: enable=g-line-too-long

    artifact = rdfvalue.Artifact(name="artifact", doc="Doco",
                                 provides=["environ_windir"],
                                 supported_os=["Windows"], urls=["http://blah"],
                                 collectors=collectors)

    self.assertItemsEqual(
        [x["collector_type"] for x in artifact.ToPrimitiveDict()["collectors"]],
        ["REGISTRY_VALUE", "WMI", "GREP"])

    class Parser1(object):
      knowledgebase_dependencies = ["appdata", "sid"]

    class Parser2(object):
      knowledgebase_dependencies = ["sid", "desktop"]

    @classmethod
    def MockGetClassesByArtifact(unused_cls, _):
      return [Parser1, Parser2]

    with utils.Stubber(parsers.Parser, "GetClassesByArtifact",
                       MockGetClassesByArtifact):
      self.assertItemsEqual(artifact.GetArtifactPathDependencies(),
                            ["appdata", "sid", "desktop", "current_control_set",
                             "users.sid", "users.username"])
