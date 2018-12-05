#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Unit test for the linux file parser."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import os
import unittest


from grr_response_core.lib import flags
from grr_response_core.lib.parsers import linux_software_parser
from grr_response_core.lib.rdfvalues import anomaly as rdf_anomaly
from grr.test_lib import test_lib

try:
  from debian import deb822  # pylint: disable=g-import-not-at-top
except ImportError:
  raise unittest.SkipTest("`deb822` not available")


class LinuxSoftwareParserTest(test_lib.GRRBaseTest):
  """Test parsing of linux software collection."""

  def testDebianPackagesStatusParser(self):
    """Test parsing of a status file."""
    parser = linux_software_parser.DebianPackagesStatusParser(deb822)
    path = os.path.join(self.base_path, "dpkg_status")
    with open(path, "rb") as data:
      out = list(parser.Parse(None, data, None))
    self.assertLen(out, 2)
    self.assertEqual(("t1", "v1"), (out[0].name, out[0].version))
    self.assertEqual(("t2", "v2"), (out[1].name, out[1].version))

  def testDebianPackagesStatusParserBadInput(self):
    """If the status file is broken, fail nicely."""
    parser = linux_software_parser.DebianPackagesStatusParser(deb822)
    path = os.path.join(self.base_path, "numbers.txt")
    with open(path, "rb") as data:
      out = list(parser.Parse(None, data, None))
    for result in out:
      self.assertIsInstance(result, rdf_anomaly.Anomaly)


def main(args):
  test_lib.main(args)


if __name__ == "__main__":
  flags.StartMain(main)
