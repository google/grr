#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Unit test for the linux file parser."""

import os


from grr.lib import flags
from grr.lib import test_lib
from grr.lib.rdfvalues import anomaly as rdf_anomaly
from grr.parsers import linux_software_parser


class LinuxSoftwareParserTest(test_lib.GRRBaseTest):
  """Test parsing of linux software collection."""

  def testDebianPackagesStatusParser(self):
    """Test parsing of a status file."""
    parser = linux_software_parser.DebianPackagesStatusParser()
    path = os.path.join(self.base_path, "dpkg_status")
    with open(path) as data:
      out = list(parser.Parse(None, data, None))
    self.assertEqual(len(out), 2)
    self.assertEqual(("t1", "v1"), (out[0].name, out[0].version))
    self.assertEqual(("t2", "v2"), (out[1].name, out[1].version))

  def testDebianPackagesStatusParserBadInput(self):
    """If the status file is broken, fail nicely."""
    parser = linux_software_parser.DebianPackagesStatusParser()
    path = os.path.join(self.base_path, "numbers.txt")
    with open(path) as data:
      out = list(parser.Parse(None, data, None))
    for result in out:
      self.assertIsInstance(result, rdf_anomaly.Anomaly)


def main(args):
  test_lib.main(args)


if __name__ == "__main__":
  flags.StartMain(main)
