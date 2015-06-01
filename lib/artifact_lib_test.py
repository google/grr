#!/usr/bin/env python
"""Tests for the artifact libraries."""

import os

# to have artifacts to test pylint: disable=unused-import
from grr.lib import artifact as _
# pylint: enable=unused-import
from grr.lib import artifact_lib
from grr.lib import artifact_registry
from grr.lib import config_lib
from grr.lib import flags
from grr.lib import parsers
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib import utils
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import test_base as rdf_test_base


class ArtifactHandlingTest(test_lib.GRRBaseTest):

  def setUp(self):
    super(ArtifactHandlingTest, self).setUp()
    test_artifacts_file = os.path.join(
        config_lib.CONFIG["Test.data_dir"], "test_artifacts.json")
    artifact_lib.LoadArtifactsFromFiles([test_artifacts_file])

  def testArtifactsValidate(self):
    """Check each artifact we have passes validation."""

    for artifact_name in artifact_registry.ArtifactRegistry.artifacts:
      art_obj = artifact_registry.ArtifactRegistry.artifacts[artifact_name]
      art_obj.Validate()

    art_obj = artifact_registry.ArtifactRegistry.artifacts["TestCmdArtifact"]
    art_obj.labels.append("BadLabel")

    self.assertRaises(artifact_registry.ArtifactDefinitionError,
                      art_obj.Validate)

  def testGetArtifacts(self):
    self.assertItemsEqual(artifact_registry.ArtifactRegistry.GetArtifacts(),
                          artifact_registry.ArtifactRegistry.artifacts.values())

    results = artifact_registry.ArtifactRegistry.GetArtifacts(os_name="Windows")
    for result in results:
      self.assertTrue("Windows" in result.supported_os or
                      not result.supported_os)

    results = artifact_registry.ArtifactRegistry.GetArtifacts(
        os_name="Windows", name_list=[
            "TestAggregationArtifact", "TestFileArtifact"])

    # TestFileArtifact doesn't match the OS criteria
    self.assertItemsEqual([x.name for x in results],
                          ["TestAggregationArtifact"])
    for result in results:
      self.assertTrue("Windows" in result.supported_os or
                      not result.supported_os)

    results = artifact_registry.ArtifactRegistry.GetArtifacts(
        os_name="Windows",
        source_type=artifact_lib.ArtifactSource.SourceType.REGISTRY_VALUE,
        name_list=["DepsProvidesMultiple"])
    self.assertEqual(results.pop().name, "DepsProvidesMultiple")

    # Check supported_os = [] matches any OS
    results = artifact_registry.ArtifactRegistry.GetArtifacts(
        os_name="Windows", name_list=["RekallPsList"])
    self.assertEqual(results.pop().name, "RekallPsList")

    results = artifact_registry.ArtifactRegistry.GetArtifacts(
        os_name="Windows", exclude_dependents=True)
    for result in results:
      self.assertFalse(result.GetArtifactPathDependencies())

    # Check provides filtering
    results = artifact_registry.ArtifactRegistry.GetArtifacts(
        os_name="Windows", provides=["users.homedir", "domain"])
    for result in results:
      # provides contains at least one of the filter strings
      self.assertTrue(len(set(result.provides).union(set(["users.homedir",
                                                          "domain"]))) >= 1)

    results = artifact_registry.ArtifactRegistry.GetArtifacts(
        os_name="Windows", provides=["nothingprovidesthis"])
    self.assertEqual(len(results), 0)

  def testGetArtifactNames(self):

    result_objs = artifact_registry.ArtifactRegistry.GetArtifacts(
        os_name="Windows", provides=["users.homedir", "domain"])

    results_names = artifact_registry.ArtifactRegistry.GetArtifactNames(
        os_name="Windows", provides=["users.homedir", "domain"])

    self.assertItemsEqual(set([a.name for a in result_objs]), results_names)

    results_names = artifact_registry.ArtifactRegistry.GetArtifactNames(
        os_name="Darwin", provides=["users.username", "domain"])
    self.assertItemsEqual(set(["OSXUsers"]), results_names)

  def testSearchDependencies(self):
    with utils.Stubber(artifact_registry.ArtifactRegistry, "artifacts", {}):
      # Just use the test artifacts to verify dependency correctness so we
      # aren't subject to changing dependencies in the whole set
      test_artifacts_file = os.path.join(config_lib.CONFIG["Test.data_dir"],
                                         "test_artifacts.json")
      artifact_lib.LoadArtifactsFromFiles([test_artifacts_file])

      names, expansions = artifact_registry.ArtifactRegistry.SearchDependencies(
          "Windows", [u"TestAggregationArtifactDeps", u"DepsParent"])

      # This list contains all artifacts that can provide the dependency, e.g.
      # DepsHomedir and DepsHomedir2 both provide
      # users.homedir.
      self.assertItemsEqual(names, [u"DepsHomedir", u"DepsHomedir2",
                                    u"DepsDesktop", u"DepsParent",
                                    u"DepsWindir", u"DepsWindirRegex",
                                    u"DepsControlSet",
                                    u"TestAggregationArtifactDeps"])

      self.assertItemsEqual(expansions, ["current_control_set", "users.homedir",
                                         "users.desktop", "environ_windir",
                                         "users.username"])

      # None of these match the OS, so we should get an empty list.
      names, expansions = artifact_registry.ArtifactRegistry.SearchDependencies(
          "Darwin", [u"TestCmdArtifact", u"TestFileArtifact"])
      self.assertItemsEqual(names, [])

  def testArtifactConversion(self):
    for art_obj in artifact_registry.ArtifactRegistry.artifacts.values():
      # Exercise conversions to ensure we can move back and forth between the
      # different forms.
      art_json = art_obj.ToPrettyJson(extended=False)
      new_art_obj = artifact_lib.ArtifactsFromYaml(art_json)[0]
      self.assertEqual(new_art_obj.ToPrimitiveDict(), art_obj.ToPrimitiveDict())

  def testArtifactsDependencies(self):
    """Check artifact dependencies work."""
    artifact_reg = artifact_registry.ArtifactRegistry.artifacts

    deps = artifact_reg["TestAggregationArtifactDeps"].GetArtifactDependencies()
    self.assertItemsEqual(list(deps), ["TestAggregationArtifact"])
    deps = artifact_reg["TestAggregationArtifactDeps"].GetArtifactDependencies(
        recursive=True)
    self.assertItemsEqual(list(deps),
                          ["TestOSAgnostic", "TestCmdArtifact",
                           "TestAggregationArtifact"])

    # Test recursive loop.
    # Make sure we use the registry registered version of the class.
    art_obj = artifact_reg["TestAggregationArtifactDeps"]
    source = art_obj.sources[0]
    backup = source.attributes["names"]
    source.attributes["names"] = ["TestAggregationArtifactDeps"]
    with self.assertRaises(RuntimeError) as e:
      deps = art_obj.GetArtifactDependencies(recursive=True)
    self.assertTrue("artifact recursion depth" in e.exception.message)
    source.attributes["names"] = backup   # Restore old source.


class ArtifactKBTest(test_lib.GRRBaseTest):

  def testInterpolation(self):
    """Check we can interpolate values from the knowledge base."""
    kb = rdf_client.KnowledgeBase()

    # No users yet, this should raise
    self.assertRaises(artifact_lib.KnowledgeBaseInterpolationError, list,
                      artifact_lib.InterpolateKbAttributes(
                          "test%%users.username%%test", kb))

    # Now we have two users
    kb.users.Append(rdf_client.KnowledgeBaseUser(username="joe", uid=1))
    kb.users.Append(rdf_client.KnowledgeBaseUser(username="jim", uid=2))
    kb.Set("environ_allusersprofile", "c:\\programdata")

    paths = artifact_lib.InterpolateKbAttributes("test%%users.username%%test",
                                                 kb)
    paths = list(paths)
    self.assertEqual(len(paths), 2)
    self.assertItemsEqual(paths, ["testjoetest", "testjimtest"])

    paths = artifact_lib.InterpolateKbAttributes(
        "%%environ_allusersprofile%%\\a", kb)
    self.assertEqual(list(paths), ["c:\\programdata\\a"])

    # Check a bad attribute raises
    self.assertRaises(
        artifact_lib.KnowledgeBaseInterpolationError, list,
        artifact_lib.InterpolateKbAttributes("%%nonexistent%%\\a", kb))

    # Empty values should also raise
    kb.Set("environ_allusersprofile", "")
    self.assertRaises(
        artifact_lib.KnowledgeBaseInterpolationError, list,
        artifact_lib.InterpolateKbAttributes(
            "%%environ_allusersprofile%%\\a", kb))

    # No users have temp defined, so this should raise
    self.assertRaises(artifact_lib.KnowledgeBaseInterpolationError, list,
                      artifact_lib.InterpolateKbAttributes(
                          "%%users.temp%%\\a", kb))

    # One user has users.temp defined, the others do not.  This is common on
    # windows where users have been created but have never logged in. We should
    # get just one value back.
    kb.users.Append(rdf_client.KnowledgeBaseUser(
        username="jason", uid=1, temp="C:\\Users\\jason\\AppData\\Local\\Temp"))
    paths = artifact_lib.InterpolateKbAttributes(
        r"%%users.temp%%\abcd", kb)
    self.assertItemsEqual(paths,
                          ["C:\\Users\\jason\\AppData\\Local\\Temp\\abcd"])


class ArtifactParserTest(test_lib.GRRBaseTest):

  def testParsersRetrieval(self):
    """Check the parsers are valid."""
    for processor in parsers.Parser.classes.values():
      if (not hasattr(processor, "output_types") or
          not isinstance(processor.output_types, (list, tuple))):
        raise parsers.ParserDefinitionError("Missing output_types on %s" %
                                            processor)

      for output_type in processor.output_types:
        if output_type not in rdfvalue.RDFValue.classes:
          raise parsers.ParserDefinitionError(
              "Parser %s has an output type that is an unknown type %s" %
              (processor, output_type))


class KnowledgeBaseUserMergeTest(test_lib.GRRBaseTest):

  def testUserMergeWindows(self):
    """Check Windows users are accurately merged."""
    kb = rdf_client.KnowledgeBase()
    self.assertEqual(len(kb.users), 0)
    kb.MergeOrAddUser(rdf_client.KnowledgeBaseUser(sid="1234"))
    self.assertEqual(len(kb.users), 1)
    kb.MergeOrAddUser(rdf_client.KnowledgeBaseUser(sid="5678",
                                                   username="test1"))
    self.assertEqual(len(kb.users), 2)

    _, conflicts = kb.MergeOrAddUser(
        rdf_client.KnowledgeBaseUser(sid="5678", username="test2"))
    self.assertEqual(len(kb.users), 2)
    self.assertEqual(conflicts[0], ("username", "test1", "test2"))
    self.assertEqual(kb.GetUser(sid="5678").username, "test2")

    # This should merge on user name as we have no other data.
    kb.MergeOrAddUser(rdf_client.KnowledgeBaseUser(username="test2",
                                                   homedir="a"))
    self.assertEqual(len(kb.users), 2)

    # This should create a new user since the sid is different.
    new_attrs, conflicts = kb.MergeOrAddUser(
        rdf_client.KnowledgeBaseUser(username="test2", sid="12345",
                                     temp="/blah"))
    self.assertEqual(len(kb.users), 3)
    self.assertItemsEqual(new_attrs, ["users.username", "users.temp",
                                      "users.sid"])
    self.assertEqual(conflicts, [])

  def testUserMergeLinux(self):
    """Check Linux users are accurately merged."""
    kb = rdf_client.KnowledgeBase()
    self.assertEqual(len(kb.users), 0)
    kb.MergeOrAddUser(rdf_client.KnowledgeBaseUser(username="blake",
                                                   last_logon=1111))
    self.assertEqual(len(kb.users), 1)
    # This should merge since the username is the same.
    kb.MergeOrAddUser(rdf_client.KnowledgeBaseUser(uid="12", username="blake"))
    self.assertEqual(len(kb.users), 1)

    # This should create a new record because the uid is different
    kb.MergeOrAddUser(
        rdf_client.KnowledgeBaseUser(username="blake",
                                     uid="13", desktop="/home/blake/Desktop"))
    self.assertEqual(len(kb.users), 2)

    kb.MergeOrAddUser(
        rdf_client.KnowledgeBaseUser(username="newblake",
                                     uid="14", desktop="/home/blake/Desktop"))

    self.assertEqual(len(kb.users), 3)

    # Check merging where we don't specify uid works
    new_attrs, conflicts = kb.MergeOrAddUser(
        rdf_client.KnowledgeBaseUser(username="newblake",
                                     desktop="/home/blakey/Desktop"))
    self.assertEqual(len(kb.users), 3)
    self.assertItemsEqual(new_attrs, ["users.username", "users.desktop"])
    self.assertItemsEqual(conflicts, [("desktop", u"/home/blake/Desktop",
                                       u"/home/blakey/Desktop")])


class ArtifactTests(rdf_test_base.RDFValueTestCase):
  """Test the Artifact implementation."""

  rdfvalue_class = artifact_lib.Artifact

  def GenerateSample(self, number=0):
    result = artifact_lib.Artifact(name="artifact%s" % number,
                                   doc="Doco",
                                   provides="environ_windir",
                                   supported_os="Windows",
                                   urls="http://blah")
    return result

  def testGetArtifactPathDependencies(self):
    sources = [
        {"type": artifact_lib.ArtifactSource.SourceType.REGISTRY_KEY,
         "attributes": {
             "keys": [r"%%current_control_set%%\Control\Session "
                      r"Manager\Environment\Path"]}},
        {"type": artifact_lib.ArtifactSource.SourceType.WMI,
         "attributes": {
             "query": "SELECT * FROM Win32_UserProfile "
                      "WHERE SID='%%users.sid%%'"}},
        {"type": artifact_lib.ArtifactSource.SourceType.GREP,
         "attributes": {
             "content_regex_list": ["^%%users.username%%:"]}}]

    artifact = artifact_lib.Artifact(name="artifact", doc="Doco",
                                     provides=["environ_windir"],
                                     supported_os=["Windows"],
                                     urls=["http://blah"],
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
        {"type": artifact_lib.ArtifactSource.SourceType.REGISTRY_KEY,
         "attributes": {
             "keys": [r"%%current_control_set%%\Control\Session "
                      r"Manager\Environment\Path"]}},
        {"type": artifact_lib.ArtifactSource.SourceType.FILE,
         "attributes": {
             "paths": [r"%%environ_systemdrive%%\Temp"]}}]

    artifact = artifact_lib.Artifact(name="good", doc="Doco",
                                     provides=["environ_windir"],
                                     supported_os=["Windows"],
                                     urls=["http://blah"],
                                     sources=sources)
    artifact.ValidateSyntax()

  def testValidateSyntaxBadProvides(self):
    sources = [
        {"type": artifact_lib.ArtifactSource.SourceType.FILE,
         "attributes": {
             "paths": [r"%%environ_systemdrive%%\Temp"]}}]

    artifact = artifact_lib.Artifact(name="bad", doc="Doco",
                                     provides=["windir"],
                                     supported_os=["Windows"],
                                     urls=["http://blah"],
                                     sources=sources)
    with self.assertRaises(artifact_registry.ArtifactDefinitionError):
      artifact.ValidateSyntax()

  def testValidateSyntaxBadPathDependency(self):
    sources = [
        {"type": artifact_lib.ArtifactSource.SourceType.FILE,
         "attributes": {
             "paths": [r"%%systemdrive%%\Temp"]}}]

    artifact = artifact_lib.Artifact(name="bad", doc="Doco",
                                     provides=["environ_windir"],
                                     supported_os=["Windows"],
                                     urls=["http://blah"],
                                     sources=sources)
    with self.assertRaises(artifact_registry.ArtifactDefinitionError):
      artifact.ValidateSyntax()


def main(argv):
  # Run the full test suite
  test_lib.GrrTestProgram(argv=argv)

if __name__ == "__main__":
  flags.StartMain(main)
