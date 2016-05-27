#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for parsers."""
import os

from grr.lib import artifact_registry
from grr.lib import config_lib
from grr.lib import flags
from grr.lib import parsers
from grr.lib import rdfvalue
from grr.lib import test_lib

# pylint: disable=unused-import
from grr.parsers import registry_init

# pylint: enable=unused-import


class ArtifactParserTests(test_lib.GRRBaseTest):
  """Test parsers validate."""

  def ValidateParser(self, parser):
    """Validate a parser is well defined."""
    for artifact_to_parse in parser.supported_artifacts:
      art_obj = artifact_registry.REGISTRY.GetArtifact(artifact_to_parse)
      if art_obj is None:
        raise parsers.ParserDefinitionError(
            "Artifact parser %s has an invalid artifact"
            " %s. Artifact is undefined" % (parser.__name__, artifact_to_parse))

    for out_type in parser.output_types:
      if out_type not in rdfvalue.RDFValue.classes:
        raise parsers.ParserDefinitionError(
            "Artifact parser %s has an invalid output "
            "type %s." % (parser.__name__, out_type))

    if parser.process_together:
      if not hasattr(parser, "ParseMultiple"):
        raise parsers.ParserDefinitionError(
            "Parser %s has set process_together, but "
            "has not defined a ParseMultiple method." % parser.__name__)

    # Additional, parser specific validation.
    parser.Validate()

  def testValidation(self):
    """Ensure all parsers pass validation."""
    test_artifacts_file = os.path.join(config_lib.CONFIG["Test.data_dir"],
                                       "artifacts", "test_artifacts.json")
    artifact_registry.REGISTRY.AddFileSource(test_artifacts_file)

    for p_cls in parsers.Parser.classes:
      parser = parsers.Parser.classes[p_cls]
      self.ValidateParser(parser)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
