#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for parsers."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

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
