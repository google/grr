#!/usr/bin/env python
"""Tests for grr.lib.rdfvalues.artifacts."""

from grr.lib import artifact_lib
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
    sources = [
        {"type": rdfvalue.ArtifactSource.SourceType.REGISTRY_KEY,
         "attributes": {
             "keys": [r"%%current_control_set%%\Control\Session "
                      r"Manager\Environment\Path"]}},
        {"type": rdfvalue.ArtifactSource.SourceType.WMI,
         "attributes": {
             "query": "SELECT * FROM Win32_UserProfile "
                      "WHERE SID='%%users.sid%%'"}},
        {"type": rdfvalue.ArtifactSource.SourceType.GREP,
         "attributes": {
             "content_regex_list": ["^%%users.username%%:"]}}]

    artifact = rdfvalue.Artifact(name="artifact", doc="Doco",
                                 provides=["environ_windir"],
                                 supported_os=["Windows"], urls=["http://blah"],
                                 sources=sources)

    self.assertItemsEqual(
        [x["type"] for x in artifact.ToPrimitiveDict()["sources"]],
        ["REGISTRY_KEY", "WMI", "GREP"])

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

  def testValidateSyntax(self):
    sources = [
        {"type": rdfvalue.ArtifactSource.SourceType.REGISTRY_KEY,
         "attributes": {
             "keys": [r"%%current_control_set%%\Control\Session "
                      r"Manager\Environment\Path"]}},
        {"type": rdfvalue.ArtifactSource.SourceType.FILE,
         "attributes": {
             "paths": [r"%%environ_systemdrive%%\Temp"]}}]

    artifact = rdfvalue.Artifact(name="good", doc="Doco",
                                 provides=["environ_windir"],
                                 supported_os=["Windows"], urls=["http://blah"],
                                 sources=sources)
    artifact.ValidateSyntax()

  def testValidateSyntaxBadProvides(self):
    sources = [
        {"type": rdfvalue.ArtifactSource.SourceType.FILE,
         "attributes": {
             "paths": [r"%%environ_systemdrive%%\Temp"]}}]

    artifact = rdfvalue.Artifact(name="bad", doc="Doco",
                                 provides=["windir"],
                                 supported_os=["Windows"], urls=["http://blah"],
                                 sources=sources)
    with self.assertRaises(artifact_lib.ArtifactDefinitionError):
      artifact.ValidateSyntax()

  def testValidateSyntaxBadPathDependency(self):
    sources = [
        {"type": rdfvalue.ArtifactSource.SourceType.FILE,
         "attributes": {
             "paths": [r"%%systemdrive%%\Temp"]}}]

    artifact = rdfvalue.Artifact(name="bad", doc="Doco",
                                 provides=["environ_windir"],
                                 supported_os=["Windows"], urls=["http://blah"],
                                 sources=sources)
    with self.assertRaises(artifact_lib.ArtifactDefinitionError):
      artifact.ValidateSyntax()

