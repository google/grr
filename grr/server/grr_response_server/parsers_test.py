#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for parsers."""
import os

from grr_response_core import config
from grr_response_core.lib import flags
from grr_response_core.lib import parser as lib_parser
from grr_response_core.lib import rdfvalue
from grr.test_lib import artifact_test_lib
from grr.test_lib import test_lib


class ArtifactParserTests(test_lib.GRRBaseTest):
  """Test parsers validate."""

  def ValidateParser(self, parser, registry):
    """Validate a parser is well defined."""
    for artifact_to_parse in parser.supported_artifacts:
      art_obj = registry.GetArtifact(artifact_to_parse)
      if art_obj is None:
        raise parser.ParserDefinitionError(
            "Artifact parser %s has an invalid artifact"
            " %s. Artifact is undefined" % (parser.__name__, artifact_to_parse))

    for out_type in parser.output_types:
      if out_type not in rdfvalue.RDFValue.classes:
        raise parser.ParserDefinitionError(
            "Artifact parser %s has an invalid output "
            "type %s." % (parser.__name__, out_type))

    if parser.process_together:
      if not hasattr(parser, "ParseMultiple"):
        raise lib_parser.ParserDefinitionError(
            "Parser %s has set process_together, but "
            "has not defined a ParseMultiple method." % parser.__name__)

    # Additional, parser specific validation.
    supported_artifact_objects = []
    for artifact_to_parse in parser.supported_artifacts:
      supported_artifact_objects.append(registry.GetArtifact(artifact_to_parse))
    parser.Validate(supported_artifact_objects)

  @artifact_test_lib.PatchDefaultArtifactRegistry
  def testValidation(self, registry):
    """Ensure all parsers pass validation."""
    test_artifacts_file = os.path.join(config.CONFIG["Test.data_dir"],
                                       "artifacts", "test_artifacts.json")
    registry.AddFileSource(test_artifacts_file)

    for p_cls in lib_parser.Parser.classes:
      parser = lib_parser.Parser.classes[p_cls]
      self.ValidateParser(parser, registry)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
