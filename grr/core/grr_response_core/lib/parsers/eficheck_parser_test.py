#!/usr/bin/env python
# Lint as: python3
"""Tests for grr.parsers.eficheck_parser."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import io
import os

from absl import app

from grr_response_core.lib.parsers import eficheck_parser
from grr.test_lib import test_lib


class TestEficheckParsing(test_lib.GRRBaseTest):
  """Test parsing of OSX files."""

  def testEficheckShowHashes(self):
    parser = eficheck_parser.EficheckCmdParser()
    test_data_path = os.path.join(self.base_path, "eficheck_show_hashes.txt")
    content = io.open(test_data_path, mode="rb").read()
    result = list(
        parser.Parse("/usr/sbin/eficheck", ["--show-hashes"], content, b"", 0,
                     None))

    self.assertLen(result, 1)
    self.assertLen(result[0].entries, 6)
    self.assertEqual(result[0].entries[0].size, 8192)
    self.assertEqual(result[0].entries[0].guid,
                     "7a9354d9-0468-444a-81ce-0bf617d890df")
    self.assertEqual(result[0].entries[0].hash,
                     ("6ba638dfa7c9a7ccf75016e98d2074c5"
                      "3e38f5ae90edfa06672aafb6c7d1c4f7"))


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
