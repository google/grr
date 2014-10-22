#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for parsers."""

# pylint: disable=unused-import
from grr import parsers
# pylint: enable=unused-import

from grr.lib import artifact_test
from grr.lib import flags
from grr.lib import parsers
from grr.lib import test_lib


class ArtifactParserTests(test_lib.GRRBaseTest):
  """Test parsers validate."""

  def testValidation(self):
    """Ensure all parsers pass validation."""
    artifact_test.ArtifactTest.LoadTestArtifacts()
    for p_cls in parsers.Parser.classes:
      parser = parsers.Parser.classes[p_cls]
      parser.Validate()


def main(argv):
  test_lib.main(argv)

if __name__ == "__main__":
  flags.StartMain(main)
