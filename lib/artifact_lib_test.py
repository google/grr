#!/usr/bin/env python
"""Tests for the artifact libraries."""

from grr.lib import artifact_lib
from grr.lib import flags
from grr.lib import parsers
from grr.lib import rdfvalue
from grr.lib import test_lib


class ArtifactTest(test_lib.GRRBaseTest):

  def testArtifactsValidate(self):
    """Check each artifact we have passes validation."""

    for a_cls in artifact_lib.Artifact.classes:
      if a_cls == "Artifact":
        continue    # Skip the base object.
      art = artifact_lib.Artifact.classes[a_cls]
      art_obj = art()
      art_obj.Validate()

    art_cls = artifact_lib.Artifact.classes["ApplicationEventLog"]
    art_obj = art_cls()
    art_obj.LABELS.append("BadLabel")

    self.assertRaises(artifact_lib.ArtifactDefinitionError, art_obj.Validate)


class ArtifactKBTest(test_lib.GRRBaseTest):

  def testInterpolation(self):
    """Check we can interpolate values from the knowledge base."""
    kb = rdfvalue.KnowledgeBase()
    kb.users.Append(rdfvalue.KnowledgeBaseUser(username="joe", uid=1))
    kb.users.Append(rdfvalue.KnowledgeBaseUser(username="jim", uid=2))
    kb.allusersprofile = "c:\\programdata"

    paths = artifact_lib.InterpolateKbAttributes("test%%users.username%%test",
                                                 kb)
    paths = list(paths)
    self.assertEquals(len(paths), 2)
    self.assertItemsEqual(paths, ["testjoetest", "testjimtest"])

    paths = artifact_lib.InterpolateKbAttributes("%%allusersprofile%%\\a", kb)
    self.assertEquals(list(paths), ["c:\\programdata\\a"])

    self.assertRaises(
        artifact_lib.KnowledgeBaseInterpolationError, list,
        artifact_lib.InterpolateKbAttributes("%%nonexistent%%\\a", kb))


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
              "Artifact %s has an output type that is an unknown type %s" %
              output_type)


def main(argv):
  test_lib.main(argv)

if __name__ == "__main__":
  flags.StartMain(main)
