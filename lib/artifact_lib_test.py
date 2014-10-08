#!/usr/bin/env python
"""Tests for the artifact libraries."""

import os

from grr.lib import artifact_lib
from grr.lib import config_lib
from grr.lib import flags
from grr.lib import parsers
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib import utils


class ArtifactHandlingTest(test_lib.GRRBaseTest):

  def setUp(self):
    super(ArtifactHandlingTest, self).setUp()
    test_artifacts_file = os.path.join(
        config_lib.CONFIG["Test.data_dir"], "test_artifacts.json")
    artifact_lib.LoadArtifactsFromFiles([test_artifacts_file])

  def testArtifactsValidate(self):
    """Check each artifact we have passes validation."""

    for artifact_name in artifact_lib.ArtifactRegistry.artifacts:
      art_obj = artifact_lib.ArtifactRegistry.artifacts[artifact_name]
      art_obj.Validate()

    art_obj = artifact_lib.ArtifactRegistry.artifacts["ApplicationEventLog"]
    art_obj.labels.append("BadLabel")

    self.assertRaises(artifact_lib.ArtifactDefinitionError, art_obj.Validate)

  def testGetArtifacts(self):
    self.assertItemsEqual(artifact_lib.ArtifactRegistry.GetArtifacts(),
                          artifact_lib.ArtifactRegistry.artifacts.values())

    results = artifact_lib.ArtifactRegistry.GetArtifacts(os_name="Windows")
    for result in results:
      self.assertTrue("Windows" in result.supported_os or
                      not result.supported_os)

    results = artifact_lib.ArtifactRegistry.GetArtifacts(
        os_name="Windows", name_list=[
            "TestAggregationArtifact", "TestFileArtifact"])

    # TestFileArtifact doesn't match the OS criteria
    self.assertItemsEqual([x.name for x in results],
                          ["TestAggregationArtifact"])
    for result in results:
      self.assertTrue("Windows" in result.supported_os or
                      not result.supported_os)

    results = artifact_lib.ArtifactRegistry.GetArtifacts(
        os_name="Windows",
        collector_type=rdfvalue.Collector.CollectorType.REGISTRY_VALUE,
        name_list=["SystemRoot"])
    self.assertEqual(results.pop().name, "SystemRoot")

    # Check supported_os = [] matches any OS
    results = artifact_lib.ArtifactRegistry.GetArtifacts(
        os_name="Windows", name_list=["RekallPsList"])
    self.assertEqual(results.pop().name, "RekallPsList")

    results = artifact_lib.ArtifactRegistry.GetArtifacts(
        os_name="Windows", exclude_dependents=True)
    for result in results:
      self.assertFalse(result.GetArtifactPathDependencies())

    # Check provides filtering
    results = artifact_lib.ArtifactRegistry.GetArtifacts(
        os_name="Windows", provides=["users.homedir", "domain"])
    for result in results:
      # provides contains at least one of the filter strings
      self.assertTrue(len(set(result.provides).union(set(["users.homedir",
                                                          "domain"]))) >= 1)

    results = artifact_lib.ArtifactRegistry.GetArtifacts(
        os_name="Windows", provides=["nothingprovidesthis"])
    self.assertEqual(len(results), 0)

  def testGetArtifactNames(self):

    result_objs = artifact_lib.ArtifactRegistry.GetArtifacts(
        os_name="Windows", provides=["users.homedir", "domain"])

    results_names = artifact_lib.ArtifactRegistry.GetArtifactNames(
        os_name="Windows", provides=["users.homedir", "domain"])

    self.assertItemsEqual(set([a.name for a in result_objs]), results_names)

    results_names = artifact_lib.ArtifactRegistry.GetArtifactNames(
        os_name="Darwin", provides=["users.username", "domain"])
    self.assertItemsEqual(set(["OSXUsers"]), results_names)

  def testSearchDependencies(self):
    with utils.Stubber(artifact_lib.ArtifactRegistry, "artifacts", {}):
      # Just use the test artifacts to verify dependency correctness so we
      # aren't subject to changing dependencies in the whole set
      test_artifacts_file = os.path.join(config_lib.CONFIG["Test.data_dir"],
                                         "test_artifacts.json")
      artifact_lib.LoadArtifactsFromFiles([test_artifacts_file])

      names, expansions = artifact_lib.ArtifactRegistry.SearchDependencies(
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
      names, expansions = artifact_lib.ArtifactRegistry.SearchDependencies(
          "Darwin", [u"TestCmdArtifact", u"TestFileArtifact"])
      self.assertItemsEqual(names, [])

  def testArtifactConversion(self):
    for art_obj in artifact_lib.ArtifactRegistry.artifacts.values():
      # Exercise conversions to ensure we can move back and forth between the
      # different forms.
      art_json = art_obj.ToPrettyJson(extended=False)
      new_art_obj = artifact_lib.ArtifactsFromYaml(art_json)[0]
      self.assertEqual(new_art_obj.ToPrimitiveDict(), art_obj.ToPrimitiveDict())

  def testArtifactsDependencies(self):
    """Check artifact dependencies work."""
    artifact_reg = artifact_lib.ArtifactRegistry.artifacts

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
    coll = art_obj.collectors[0]
    backup = coll.args["artifact_list"]
    coll.args["artifact_list"] = ["TestAggregationArtifactDeps"]
    with self.assertRaises(RuntimeError) as e:
      deps = art_obj.GetArtifactDependencies(recursive=True)
    self.assertTrue("artifact recursion depth" in e.exception.message)
    coll.args["artifact_list"] = backup   # Restore old collector.


class ArtifactKBTest(test_lib.GRRBaseTest):

  def testInterpolation(self):
    """Check we can interpolate values from the knowledge base."""
    kb = rdfvalue.KnowledgeBase()
    self.assertRaises(artifact_lib.KnowledgeBaseInterpolationError, list,
                      artifact_lib.InterpolateKbAttributes(
                          "test%%users.username%%test", kb))
    kb.users.Append(rdfvalue.KnowledgeBaseUser(username="joe", uid=1))
    kb.users.Append(rdfvalue.KnowledgeBaseUser(username="jim", uid=2))
    kb.Set("environ_allusersprofile", "c:\\programdata")

    paths = artifact_lib.InterpolateKbAttributes("test%%users.username%%test",
                                                 kb)
    paths = list(paths)
    self.assertEqual(len(paths), 2)
    self.assertItemsEqual(paths, ["testjoetest", "testjimtest"])

    paths = artifact_lib.InterpolateKbAttributes(
        "%%environ_allusersprofile%%\\a", kb)
    self.assertEqual(list(paths), ["c:\\programdata\\a"])

    self.assertRaises(
        artifact_lib.KnowledgeBaseInterpolationError, list,
        artifact_lib.InterpolateKbAttributes("%%nonexistent%%\\a", kb))

    kb.Set("environ_allusersprofile", "")
    self.assertRaises(
        artifact_lib.KnowledgeBaseInterpolationError, list,
        artifact_lib.InterpolateKbAttributes(
            "%%environ_allusersprofile%%\\a", kb))


class ArtifactParserTest(test_lib.GRRBaseTest):

  def testParsersRetrieval(self):
    """Check the parsers are valid."""
    for processor in parsers.Parser.classes.values():
      if (not hasattr(processor, "output_types") or
          not isinstance(processor.output_types, (list, tuple))):
        raise parsers.ParserDefinitionError("Missing output_types on %s" %
                                            processor)

      for output_type in processor.output_types:
        if not hasattr(rdfvalue, output_type):
          raise parsers.ParserDefinitionError(
              "Parser %s has an output type that is an unknown type %s" %
              (processor, output_type))


class KnowledgeBaseUserMergeTest(test_lib.GRRBaseTest):

  def testUserMergeWindows(self):
    """Check Windows users are accurately merged."""
    kb = rdfvalue.KnowledgeBase()
    self.assertEqual(len(kb.users), 0)
    kb.MergeOrAddUser(rdfvalue.KnowledgeBaseUser(sid="1234"))
    self.assertEqual(len(kb.users), 1)
    kb.MergeOrAddUser(rdfvalue.KnowledgeBaseUser(sid="5678", username="test1"))
    self.assertEqual(len(kb.users), 2)

    _, conflicts = kb.MergeOrAddUser(
        rdfvalue.KnowledgeBaseUser(sid="5678", username="test2"))
    self.assertEqual(len(kb.users), 2)
    self.assertEqual(conflicts[0], ("username", "test1", "test2"))
    self.assertEqual(kb.GetUser(sid="5678").username, "test2")

    # This should merge on user name as we have no other data.
    kb.MergeOrAddUser(rdfvalue.KnowledgeBaseUser(username="test2", homedir="a"))
    self.assertEqual(len(kb.users), 2)

    # This should create a new user since the sid is different.
    new_attrs, conflicts = kb.MergeOrAddUser(
        rdfvalue.KnowledgeBaseUser(username="test2", sid="12345", temp="/blah"))
    self.assertEqual(len(kb.users), 3)
    self.assertItemsEqual(new_attrs, ["users.username", "users.temp",
                                      "users.sid"])
    self.assertEqual(conflicts, [])

  def testUserMergeLinux(self):
    """Check Linux users are accurately merged."""
    kb = rdfvalue.KnowledgeBase()
    self.assertEqual(len(kb.users), 0)
    kb.MergeOrAddUser(rdfvalue.KnowledgeBaseUser(username="blake",
                                                 last_logon=1111))
    self.assertEqual(len(kb.users), 1)
    # This should merge since the username is the same.
    kb.MergeOrAddUser(rdfvalue.KnowledgeBaseUser(uid="12", username="blake"))
    self.assertEqual(len(kb.users), 1)

    # This should create a new record because the uid is different
    kb.MergeOrAddUser(
        rdfvalue.KnowledgeBaseUser(username="blake",
                                   uid="13", desktop="/home/blake/Desktop"))
    self.assertEqual(len(kb.users), 2)

    kb.MergeOrAddUser(
        rdfvalue.KnowledgeBaseUser(username="newblake",
                                   uid="14", desktop="/home/blake/Desktop"))

    self.assertEqual(len(kb.users), 3)

    # Check merging where we don't specify uid works
    new_attrs, conflicts = kb.MergeOrAddUser(
        rdfvalue.KnowledgeBaseUser(username="newblake",
                                   desktop="/home/blakey/Desktop"))
    self.assertEqual(len(kb.users), 3)
    self.assertItemsEqual(new_attrs, ["users.username", "users.desktop"])
    self.assertItemsEqual(conflicts, [("desktop", u"/home/blake/Desktop",
                                       u"/home/blakey/Desktop")])


def main(argv):
  test_lib.main(argv)

if __name__ == "__main__":
  flags.StartMain(main)
