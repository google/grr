#!/usr/bin/env python
"""Tests for the artifact libraries."""

import os

from grr.lib import artifact_lib
from grr.lib import config_lib
from grr.lib import flags
from grr.lib import parsers
from grr.lib import rdfvalue
from grr.lib import test_lib


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
        os_name="Windows", collector_action="Bootstrap",
        name_list=["SystemRoot"])
    self.assertEqual(results.pop().name, "SystemRoot")

    # Check supported_os = [] matches any OS
    results = artifact_lib.ArtifactRegistry.GetArtifacts(
        os_name="Windows", name_list=["VolatilityPsList"])
    self.assertEqual(results.pop().name, "VolatilityPsList")

  def testArtifactConversion(self):
    for art_obj in artifact_lib.ArtifactRegistry.artifacts.values():
      # Exercise conversions to ensure we can move back and forth between the
      # different forms.
      art_json = art_obj.ToPrettyJson(extended=True)
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
                          ["VolatilityPsList", "TestAggregationArtifact",
                           "WindowsWMIInstalledSoftware"])

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
    kb.users.Append(rdfvalue.KnowledgeBaseUser(username="joe", uid=1))
    kb.users.Append(rdfvalue.KnowledgeBaseUser(username="jim", uid=2))
    kb.Set("environ_allusersprofile", "c:\\programdata")

    paths = artifact_lib.InterpolateKbAttributes("test%%users.username%%test",
                                                 kb)
    paths = list(paths)
    self.assertEquals(len(paths), 2)
    self.assertItemsEqual(paths, ["testjoetest", "testjimtest"])

    paths = artifact_lib.InterpolateKbAttributes(
        "%%environ_allusersprofile%%\\a", kb)
    self.assertEquals(list(paths), ["c:\\programdata\\a"])

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

  def testUserMerge(self):
    """Check users are accurately merged."""
    kb = rdfvalue.KnowledgeBase()
    self.assertEquals(len(kb.users), 0)
    kb.MergeOrAddUser(rdfvalue.KnowledgeBaseUser(sid="1234"))
    self.assertEquals(len(kb.users), 1)
    kb.MergeOrAddUser(rdfvalue.KnowledgeBaseUser(sid="5678", username="test1"))
    self.assertEquals(len(kb.users), 2)

    _, conflicts = kb.MergeOrAddUser(
        rdfvalue.KnowledgeBaseUser(sid="5678", username="test2"))
    self.assertEquals(len(kb.users), 2)
    self.assertEquals(conflicts[0], ("username", "test1", "test2"))
    self.assertEquals(kb.GetUser(sid="5678").username, "test2")

    # This should merge on user name as we have no other data.
    kb.MergeOrAddUser(rdfvalue.KnowledgeBaseUser(username="test2", homedir="a"))
    self.assertEquals(len(kb.users), 2)


def main(argv):
  test_lib.main(argv)

if __name__ == "__main__":
  flags.StartMain(main)
