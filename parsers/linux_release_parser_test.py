#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

"""Unit test for the linux distribution parser."""

import os


from grr.lib import flags
from grr.lib import test_lib
from grr.lib.rdfvalues import anomaly as rdf_anomaly
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import paths as rdf_paths
from grr.lib.rdfvalues import protodict as rdf_protodict
from grr.parsers import linux_release_parser


class LinuxReleaseParserTest(test_lib.GRRBaseTest):
  """Test parsing of linux distribution collection."""

  def testMalformedLsbReleaseFile(self):
    path = os.path.join(self.base_path, "lsb-release-bad")
    with open(path) as f:
      data = f.read()
    parser = linux_release_parser.LsbReleaseParseHandler(data)

    complete, result = parser.Parse()

    self.assertFalse(complete)
    self.assertTupleEqual((None, 0, 0), result)

  def testGoodLsbReleaseFile(self):
    path = os.path.join(self.base_path, "lsb-release")
    with open(path) as f:
      data = f.read()
    parser = linux_release_parser.LsbReleaseParseHandler(data)

    complete, result = parser.Parse()

    self.assertTrue(complete)
    self.assertTupleEqual(("Ubuntu", 14, 4), result)

  def testFallbackLsbReleaseFile(self):
    path = os.path.join(self.base_path, "lsb-release-notubuntu")
    with open(path) as f:
      data = f.read()
    parser = linux_release_parser.LsbReleaseParseHandler(data)

    complete, result = parser.Parse()

    self.assertFalse(complete)
    self.assertTupleEqual(("NotUbuntu", 0, 0), result)

  def testReleaseFileRedHatish(self):
    path = os.path.join(self.base_path, "oracle-release")
    with open(path) as f:
      data = f.read()
    parser = linux_release_parser.ReleaseFileParseHandler("OracleLinux")
    parser(data)

    complete, result = parser.Parse()

    self.assertTrue(complete)
    self.assertTupleEqual(("OracleLinux", 6, 5), result)

  def testMalformedReleaseFileRedHatish(self):
    path = os.path.join(self.base_path, "oracle-release-bad")
    with open(path) as f:
      data = f.read()
    parser = linux_release_parser.ReleaseFileParseHandler("OracleLinux")
    parser(data)

    complete, result = parser.Parse()

    self.assertFalse(complete)
    self.assertTupleEqual(("OracleLinux", 0, 0), result)

  def _CreateTestData(self, testdata):
    """Create 'stats' and 'file_objects' lists for passing to ParseMultiple."""
    stats = []
    files = []
    for filepath, localfile in testdata:
      files.append(open(localfile))

      p = rdf_paths.PathSpec(path=filepath)
      s = rdf_client.StatEntry(pathspec=p)
      stats.append(s)

    return stats, files

  def testEndToEndUbuntu(self):
    parser = linux_release_parser.LinuxReleaseParser()

    testdata = [
        ("/etc/lsb-release", os.path.join(self.base_path, "lsb-release")),
    ]
    stats, files = self._CreateTestData(testdata)

    result = list(parser.ParseMultiple(stats, files, None)).pop()

    self.assertIsInstance(result, rdf_protodict.Dict)
    self.assertEqual("Ubuntu", result["os_release"])
    self.assertEqual(14, result["os_major_version"])
    self.assertEqual(4, result["os_minor_version"])

  def testEndToEndOracleLinux(self):
    parser = linux_release_parser.LinuxReleaseParser()

    testdata = [
        ("/etc/lsb-release", os.path.join(self.base_path,
                                          "lsb-release-notubuntu")),
        ("/etc/oracle-release", os.path.join(self.base_path, "oracle-release")),
    ]
    stats, files = self._CreateTestData(testdata)

    result = list(parser.ParseMultiple(stats, files, None)).pop()

    self.assertIsInstance(result, rdf_protodict.Dict)
    self.assertEqual("OracleLinux", result["os_release"])
    self.assertEqual(6, result["os_major_version"])
    self.assertEqual(5, result["os_minor_version"])

  def testAnomaly(self):
    parser = linux_release_parser.LinuxReleaseParser()

    stats = []
    files = []
    result = list(parser.ParseMultiple(stats, files, None))

    self.assertEqual(len(result), 1)
    self.assertIsInstance(result[0], rdf_anomaly.Anomaly)


def main(args):
  test_lib.main(args)

if __name__ == "__main__":
  flags.StartMain(main)
