#!/usr/bin/env python
"""Tests for the artifact libraries."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import os

from future.utils import itervalues

from grr_response_core.lib import artifact_utils
from grr_response_core.lib import flags
from grr_response_core.lib import parser
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import artifacts as rdf_artifacts
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import test_base as rdf_test_base
from grr_response_server import artifact_registry as ar
from grr.test_lib import artifact_test_lib
from grr.test_lib import test_lib


class ArtifactHandlingTest(test_lib.GRRBaseTest):

  def setUp(self):
    super(ArtifactHandlingTest, self).setUp()
    self.test_artifacts_dir = os.path.join(self.base_path, "artifacts")
    self.test_artifacts_file = os.path.join(self.test_artifacts_dir,
                                            "test_artifacts.json")

  @artifact_test_lib.PatchCleanArtifactRegistry
  def testArtifactsValidate(self, registry):
    """Check each artifact we have passes validation."""
    registry.AddFileSource(self.test_artifacts_file)

    for artifact in registry.GetArtifacts():
      ar.Validate(artifact)

    art_obj = registry.GetArtifact("TestCmdArtifact")
    art_obj.labels.append("BadLabel")

    self.assertRaises(rdf_artifacts.ArtifactDefinitionError, ar.Validate,
                      art_obj)

  @artifact_test_lib.PatchCleanArtifactRegistry
  def testAddFileSource(self, registry):
    registry.AddFileSource(self.test_artifacts_file)
    registry.GetArtifact("TestCmdArtifact")
    with self.assertRaises(rdf_artifacts.ArtifactNotRegisteredError):
      registry.GetArtifact("NonExistentArtifact")

  @artifact_test_lib.PatchCleanArtifactRegistry
  def testAddDirSource(self, registry):
    registry.AddDirSource(self.test_artifacts_dir)
    registry.GetArtifact("TestCmdArtifact")
    with self.assertRaises(rdf_artifacts.ArtifactNotRegisteredError):
      registry.GetArtifact("NonExistentArtifact")

  @artifact_test_lib.PatchDefaultArtifactRegistry
  def testGetArtifacts(self, registry):
    registry.AddFileSource(self.test_artifacts_file)

    results = registry.GetArtifacts(os_name="Windows")
    for result in results:
      self.assertTrue("Windows" in result.supported_os or
                      not result.supported_os)

    results = registry.GetArtifacts(
        os_name="Windows",
        name_list=["TestAggregationArtifact", "TestFileArtifact"])

    # TestFileArtifact doesn't match the OS criteria
    self.assertCountEqual([x.name for x in results],
                          ["TestAggregationArtifact"])
    for result in results:
      self.assertTrue("Windows" in result.supported_os or
                      not result.supported_os)

    results = registry.GetArtifacts(
        os_name="Windows",
        source_type=rdf_artifacts.ArtifactSource.SourceType.REGISTRY_VALUE,
        name_list=["DepsProvidesMultiple"])
    self.assertEqual(results.pop().name, "DepsProvidesMultiple")

    # Check supported_os = [] matches any OS
    results = registry.GetArtifacts(
        os_name="Windows", name_list=["RekallPsList"])
    self.assertLen(results, 1)
    self.assertEqual(results.pop().name, "RekallPsList")

    results = registry.GetArtifacts(os_name="Windows", exclude_dependents=True)
    for result in results:
      self.assertFalse(ar.GetArtifactPathDependencies(result))

    # Check provides filtering
    results = registry.GetArtifacts(
        os_name="Windows", provides=["users.homedir", "domain"])
    for result in results:
      # provides contains at least one of the filter strings
      self.assertTrue(
          len(set(result.provides).union(set(["users.homedir", "domain"]))) >= 1
      )

    results = registry.GetArtifacts(
        os_name="Windows", provides=["nothingprovidesthis"])
    self.assertEmpty(results)

  @artifact_test_lib.PatchDefaultArtifactRegistry
  def testGetArtifactNames(self, registry):
    registry.AddFileSource(self.test_artifacts_file)

    result_objs = registry.GetArtifacts(
        os_name="Windows", provides=["users.homedir", "domain"])

    results_names = registry.GetArtifactNames(
        os_name="Windows", provides=["users.homedir", "domain"])

    self.assertCountEqual(set([a.name for a in result_objs]), results_names)
    self.assertTrue(len(results_names))

    results_names = registry.GetArtifactNames(
        os_name="Darwin", provides=["users.username"])
    self.assertIn("MacOSUsers", results_names)

  @artifact_test_lib.PatchCleanArtifactRegistry
  def testSearchDependencies(self, registry):
    registry.AddFileSource(self.test_artifacts_file)

    names, expansions = registry.SearchDependencies(
        "Windows", [u"TestAggregationArtifactDeps", u"DepsParent"])

    # This list contains all artifacts that can provide the dependency, e.g.
    # DepsHomedir and DepsHomedir2 both provide
    # users.homedir.
    self.assertCountEqual(names, [
        u"DepsHomedir", u"DepsHomedir2", u"DepsDesktop", u"DepsParent",
        u"DepsWindir", u"DepsWindirRegex", u"DepsControlSet",
        u"TestAggregationArtifactDeps"
    ])

    self.assertCountEqual(expansions, [
        "current_control_set", "users.homedir", "users.desktop",
        "environ_windir", "users.username"
    ])

    # None of these match the OS, so we should get an empty list.
    names, expansions = registry.SearchDependencies(
        "Darwin", [u"TestCmdArtifact", u"TestFileArtifact"])
    self.assertCountEqual(names, [])

  @artifact_test_lib.PatchCleanArtifactRegistry
  def testArtifactConversion(self, registry):
    registry.AddFileSource(self.test_artifacts_file)

    for art_obj in registry.GetArtifacts():
      # Exercise conversions to ensure we can move back and forth between the
      # different forms.
      art_json = art_obj.ToJson()
      new_art_obj = registry.ArtifactsFromYaml(art_json)[0]
      self.assertEqual(new_art_obj.ToPrimitiveDict(), art_obj.ToPrimitiveDict())

  @artifact_test_lib.PatchCleanArtifactRegistry
  def testArtifactsDependencies(self, registry):
    """Check artifact dependencies work."""
    registry.AddFileSource(self.test_artifacts_file)

    art_obj = registry.GetArtifact("TestAggregationArtifactDeps")
    deps = ar.GetArtifactDependencies(art_obj)
    self.assertCountEqual(list(deps), ["TestAggregationArtifact"])

    deps = ar.GetArtifactDependencies(art_obj, recursive=True)
    self.assertCountEqual(
        list(deps),
        ["TestOSAgnostic", "TestCmdArtifact", "TestAggregationArtifact"])

    # Test recursive loop.
    # Make sure we use the registry registered version of the class.
    source = art_obj.sources[0]
    backup = source.attributes["names"]
    try:
      source.attributes["names"] = ["TestAggregationArtifactDeps"]
      with self.assertRaises(RuntimeError) as e:
        deps = ar.GetArtifactDependencies(art_obj, recursive=True)
      self.assertIn("artifact recursion depth", e.exception.message)
    finally:
      source.attributes["names"] = backup  # Restore old source.


class ArtifactKBTest(test_lib.GRRBaseTest):

  def testInterpolation(self):
    """Check we can interpolate values from the knowledge base."""
    kb = rdf_client.KnowledgeBase()

    # No users yet, this should raise
    self.assertRaises(
        artifact_utils.KnowledgeBaseInterpolationError, list,
        artifact_utils.InterpolateKbAttributes("test%%users.username%%test",
                                               kb))

    # Now we have two users
    kb.users.Append(rdf_client.User(username="joe", uid=1))
    kb.users.Append(rdf_client.User(username="jim", uid=2))
    kb.Set("environ_allusersprofile", "c:\\programdata")

    paths = artifact_utils.InterpolateKbAttributes("test%%users.username%%test",
                                                   kb)
    paths = list(paths)
    self.assertLen(paths, 2)
    self.assertCountEqual(paths, ["testjoetest", "testjimtest"])

    paths = artifact_utils.InterpolateKbAttributes(
        "%%environ_allusersprofile%%\\a", kb)
    self.assertEqual(list(paths), ["c:\\programdata\\a"])

    # Check a bad attribute raises
    self.assertRaises(
        artifact_utils.KnowledgeBaseInterpolationError, list,
        artifact_utils.InterpolateKbAttributes("%%nonexistent%%\\a", kb))

    # Empty values should also raise
    kb.Set("environ_allusersprofile", "")
    self.assertRaises(
        artifact_utils.KnowledgeBaseInterpolationError, list,
        artifact_utils.InterpolateKbAttributes("%%environ_allusersprofile%%\\a",
                                               kb))

    # No users have temp defined, so this should raise
    self.assertRaises(
        artifact_utils.KnowledgeBaseInterpolationError, list,
        artifact_utils.InterpolateKbAttributes("%%users.temp%%\\a", kb))

    # One user has users.temp defined, the others do not.  This is common on
    # windows where users have been created but have never logged in. We should
    # get just one value back.
    kb.users.Append(
        rdf_client.User(
            username="jason",
            uid=1,
            temp="C:\\Users\\jason\\AppData\\Local\\Temp"))
    paths = artifact_utils.InterpolateKbAttributes(r"%%users.temp%%\abcd", kb)
    self.assertCountEqual(paths,
                          ["C:\\Users\\jason\\AppData\\Local\\Temp\\abcd"])


class ArtifactParserTest(test_lib.GRRBaseTest):

  def testParsersRetrieval(self):
    """Check the parsers are valid."""
    for processor in itervalues(parser.Parser.classes):
      if (not hasattr(processor, "output_types") or
          not isinstance(processor.output_types, (list, tuple))):
        raise parser.ParserDefinitionError(
            "Missing output_types on %s" % processor)

      for output_type in processor.output_types:
        if output_type not in rdfvalue.RDFValue.classes:
          raise parser.ParserDefinitionError(
              "Parser %s has an output type that is an unknown type %s" %
              (processor, output_type))


class UserMergeTest(test_lib.GRRBaseTest):

  def testUserMergeWindows(self):
    """Check Windows users are accurately merged."""
    kb = rdf_client.KnowledgeBase()
    self.assertEmpty(kb.users)
    kb.MergeOrAddUser(rdf_client.User(sid="1234"))
    self.assertLen(kb.users, 1)
    kb.MergeOrAddUser(rdf_client.User(sid="5678", username="test1"))
    self.assertLen(kb.users, 2)

    _, conflicts = kb.MergeOrAddUser(
        rdf_client.User(sid="5678", username="test2"))
    self.assertLen(kb.users, 2)
    self.assertEqual(conflicts[0], ("username", "test1", "test2"))
    self.assertEqual(kb.GetUser(sid="5678").username, "test2")

    # This should merge on user name as we have no other data.
    kb.MergeOrAddUser(rdf_client.User(username="test2", homedir="a"))
    self.assertLen(kb.users, 2)

    # This should create a new user since the sid is different.
    new_attrs, conflicts = kb.MergeOrAddUser(
        rdf_client.User(username="test2", sid="12345", temp="/blah"))
    self.assertLen(kb.users, 3)
    self.assertCountEqual(new_attrs,
                          ["users.username", "users.temp", "users.sid"])
    self.assertEqual(conflicts, [])

  def testUserMergeLinux(self):
    """Check Linux users are accurately merged."""
    kb = rdf_client.KnowledgeBase()
    self.assertEmpty(kb.users)
    kb.MergeOrAddUser(rdf_client.User(username="blake", last_logon=1111))
    self.assertLen(kb.users, 1)
    # This should merge since the username is the same.
    kb.MergeOrAddUser(rdf_client.User(uid="12", username="blake"))
    self.assertLen(kb.users, 1)

    # This should create a new record because the uid is different
    kb.MergeOrAddUser(
        rdf_client.User(
            username="blake", uid="13", desktop="/home/blake/Desktop"))
    self.assertLen(kb.users, 2)

    kb.MergeOrAddUser(
        rdf_client.User(
            username="newblake", uid="14", desktop="/home/blake/Desktop"))

    self.assertLen(kb.users, 3)

    # Check merging where we don't specify uid works
    new_attrs, conflicts = kb.MergeOrAddUser(
        rdf_client.User(username="newblake", desktop="/home/blakey/Desktop"))
    self.assertLen(kb.users, 3)
    self.assertCountEqual(new_attrs, ["users.username", "users.desktop"])
    self.assertCountEqual(
        conflicts,
        [("desktop", u"/home/blake/Desktop", u"/home/blakey/Desktop")])


class ArtifactTests(rdf_test_base.RDFValueTestMixin, test_lib.GRRBaseTest):
  """Test the Artifact implementation."""

  rdfvalue_class = rdf_artifacts.Artifact

  def GenerateSample(self, number=0):
    result = rdf_artifacts.Artifact(
        name="artifact%s" % number,
        doc="Doco",
        provides="environ_windir",
        supported_os="Windows",
        urls="http://blah")
    return result

  def testGetArtifactPathDependencies(self):
    sources = [{
        "type": rdf_artifacts.ArtifactSource.SourceType.REGISTRY_KEY,
        "attributes": {
            "keys": [
                r"%%current_control_set%%\Control\Session "
                r"Manager\Environment\Path"
            ]
        }
    },
               {
                   "type": rdf_artifacts.ArtifactSource.SourceType.WMI,
                   "attributes": {
                       "query": "SELECT * FROM Win32_UserProfile "
                                "WHERE SID='%%users.sid%%'"
                   }
               },
               {
                   "type": rdf_artifacts.ArtifactSource.SourceType.GREP,
                   "attributes": {
                       "content_regex_list": ["^%%users.username%%:"]
                   }
               }]

    artifact = rdf_artifacts.Artifact(
        name="artifact",
        doc="Doco",
        provides=["environ_windir"],
        supported_os=["Windows"],
        urls=["http://blah"],
        sources=sources)

    self.assertCountEqual(
        [x["type"] for x in artifact.ToPrimitiveDict()["sources"]],
        ["REGISTRY_KEY", "WMI", "GREP"])

    class Parser1(object):
      knowledgebase_dependencies = ["appdata", "sid"]

    class Parser2(object):
      knowledgebase_dependencies = ["sid", "desktop"]

    @classmethod
    def MockGetClassesByArtifact(unused_cls, _):
      return [Parser1, Parser2]

    with utils.Stubber(parser.Parser, "GetClassesByArtifact",
                       MockGetClassesByArtifact):
      self.assertCountEqual(
          ar.GetArtifactPathDependencies(artifact), [
              "appdata", "sid", "desktop", "current_control_set", "users.sid",
              "users.username"
          ])

  def testValidateSyntax(self):
    sources = [{
        "type": rdf_artifacts.ArtifactSource.SourceType.REGISTRY_KEY,
        "attributes": {
            "keys": [
                r"%%current_control_set%%\Control\Session "
                r"Manager\Environment\Path"
            ]
        }
    },
               {
                   "type": rdf_artifacts.ArtifactSource.SourceType.FILE,
                   "attributes": {
                       "paths": [r"%%environ_systemdrive%%\Temp"]
                   }
               }]

    artifact = rdf_artifacts.Artifact(
        name="good",
        doc="Doco",
        provides=["environ_windir"],
        supported_os=["Windows"],
        urls=["http://blah"],
        sources=sources)
    ar.ValidateSyntax(artifact)

  def testValidateSyntaxBadProvides(self):
    sources = [{
        "type": rdf_artifacts.ArtifactSource.SourceType.FILE,
        "attributes": {
            "paths": [r"%%environ_systemdrive%%\Temp"]
        }
    }]

    artifact = rdf_artifacts.Artifact(
        name="bad",
        doc="Doco",
        provides=["windir"],
        supported_os=["Windows"],
        urls=["http://blah"],
        sources=sources)
    with self.assertRaises(rdf_artifacts.ArtifactDefinitionError):
      ar.ValidateSyntax(artifact)

  def testValidateSyntaxBadPathDependency(self):
    sources = [{
        "type": rdf_artifacts.ArtifactSource.SourceType.FILE,
        "attributes": {
            "paths": [r"%%systemdrive%%\Temp"]
        }
    }]

    artifact = rdf_artifacts.Artifact(
        name="bad",
        doc="Doco",
        provides=["environ_windir"],
        supported_os=["Windows"],
        urls=["http://blah"],
        sources=sources)
    with self.assertRaises(rdf_artifacts.ArtifactDefinitionError):
      ar.ValidateSyntax(artifact)


class GetWindowsEnvironmentVariablesMapTest(test_lib.GRRBaseTest):

  def testKnowledgeBaseRootAttributesGetMappedCorrectly(self):
    kb = rdf_client.KnowledgeBase(
        environ_path="the_path",
        environ_temp="the_temp",
        environ_systemroot="the_systemroot",
        environ_windir="the_windir",
        environ_programfiles="the_programfiles",
        environ_programfilesx86="the_programfilesx86",
        environ_systemdrive="the_systemdrive",
        environ_allusersprofile="the_allusersprofile",
        environ_allusersappdata="the_allusersappdata")

    mapping = artifact_utils.GetWindowsEnvironmentVariablesMap(kb)

    self.assertEqual(
        mapping, {
            "allusersappdata": "the_allusersappdata",
            "allusersprofile": "the_allusersprofile",
            "path": "the_path",
            "programdata": "the_allusersprofile",
            "programfiles": "the_programfiles",
            "programfiles(x86)": "the_programfilesx86",
            "programw6432": "the_programfiles",
            "systemdrive": "the_systemdrive",
            "systemroot": "the_systemroot",
            "temp": "the_temp",
            "windir": "the_windir"
        })

  def testKnowlegeBaseUsersAttributesExpandIntoLists(self):
    kb = rdf_client.KnowledgeBase()
    kb.users.append(
        rdf_client.User(
            appdata="the_appdata_1",
            localappdata="the_localappdata_1",
            userdomain="the_userdomain_1",
            userprofile="the_userprofile_1"))
    kb.users.append(
        rdf_client.User(
            appdata="the_appdata_2",
            localappdata="the_localappdata_2",
            userdomain="the_userdomain_2",
            userprofile="the_userprofile_2"))

    mapping = artifact_utils.GetWindowsEnvironmentVariablesMap(kb)

    self.assertEqual(
        mapping, {
            "appdata": ["the_appdata_1", "the_appdata_2"],
            "localappdata": ["the_localappdata_1", "the_localappdata_2"],
            "userdomain": ["the_userdomain_1", "the_userdomain_2"],
            "userprofile": ["the_userprofile_1", "the_userprofile_2"]
        })


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
